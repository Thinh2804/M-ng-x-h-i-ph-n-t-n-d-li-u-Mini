"""Service kết hợp 2 mô hình: Neo4j (đồ thị) + MongoDB (tài liệu)."""
from pymongo.errors import PyMongoError
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from .. import database as dbx

GRAPH_DOWN = {"degraded": True, "reason": "Neo4j không khả dụng"}


def get_friend_ids(user_id: str) -> list[str]:
    with dbx.neo4j_driver.session() as s:
        res = s.run("MATCH (:User {id:$id})-[:FRIEND]->(f:User) RETURN f.id AS id", id=user_id)
        return [r["id"] for r in res]


def news_feed(user_id: str, limit: int = 20) -> dict:
    """Feed = bạn bè từ Neo4j → bài viết từ MongoDB (liên mô hình, liên nút)."""
    try:
        friend_ids = get_friend_ids(user_id)
    except (Neo4jError, ServiceUnavailable, OSError):
        # Neo4j chết: degraded - trả bài viết của chính mình từ Mongo
        posts = list(
            dbx.db_secondary.posts.find({"author_id": user_id})
            .sort("created_at", -1).limit(limit)
        )
        return {**GRAPH_DOWN, "posts": posts}

    author_ids = friend_ids + [user_id]
    # Truy vấn scatter-gather: author_ids nằm rải trên nhiều shard
    posts = list(
        dbx.db.posts.find({"author_id": {"$in": author_ids}})
        .sort("created_at", -1).limit(limit)
    )
    # Gắn thông tin tác giả (join thủ công trong Mongo)
    users = {u["_id"]: u for u in dbx.db.users.find({"_id": {"$in": author_ids}})}
    for p in posts:
        a = users.get(p["author_id"], {})
        p["author_name"] = a.get("full_name") or a.get("username", "?")
    return {"degraded": False, "friend_count": len(friend_ids), "posts": posts}


def suggest_friends(user_id: str, limit: int = 10) -> dict:
    """Gợi ý kết bạn: friend-of-friend (Neo4j) + làm giàu hồ sơ (MongoDB)."""
    try:
        with dbx.neo4j_driver.session() as s:
            res = s.run(
                """MATCH (me:User {id:$id})-[:FRIEND]->()-[:FRIEND]->(fof:User)
                   WHERE fof.id <> $id AND NOT (me)-[:FRIEND]->(fof)
                   RETURN fof.id AS id, count(*) AS mutual
                   ORDER BY mutual DESC LIMIT $limit""",
                id=user_id, limit=limit,
            )
            cands = [{"user_id": r["id"], "mutual_friends": r["mutual"]} for r in res]
    except (Neo4jError, ServiceUnavailable, OSError):
        return {**GRAPH_DOWN, "suggestions": []}

    ids = [c["user_id"] for c in cands]
    try:
        profiles = {u["_id"]: u for u in dbx.db.users.find({"_id": {"$in": ids}})}
        for c in cands:
            p = profiles.get(c["user_id"], {})
            c["username"] = p.get("username", "?")
            c["full_name"] = p.get("full_name", "")
            c["post_count"] = dbx.db.posts.count_documents({"author_id": c["user_id"]})
    except PyMongoError:
        pass
    return {"degraded": False, "suggestions": cands}


def detect_communities(limit: int = 20) -> dict:
    """Phát hiện cộng đồng đơn giản bằng thành phần liên thông (Cypher thuần)."""
    try:
        with dbx.neo4j_driver.session() as s:
            res = s.run(
                """MATCH (u:User)
                   OPTIONAL MATCH path = (u)-[:FRIEND*1..3]-(other:User)
                   WITH u, collect(DISTINCT other.id) + u.id AS members
                   RETURN u.id AS seed, members
                   LIMIT $limit""",
                limit=limit,
            )
            raw = [(r["seed"], frozenset(r["members"])) for r in res]
    except (Neo4jError, ServiceUnavailable, OSError):
        return {**GRAPH_DOWN, "communities": []}

    seen, communities = set(), []
    for _, members in sorted(raw, key=lambda x: -len(x[1])):
        if members & seen:
            continue
        seen |= members
        communities.append({"size": len(members), "members": sorted(members)[:10]})
    return {"degraded": False, "communities": communities}
