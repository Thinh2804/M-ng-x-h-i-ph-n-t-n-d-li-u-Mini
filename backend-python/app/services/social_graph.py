"""Service kết hợp 2 mô hình: Neo4j (đồ thị) + MongoDB (tài liệu)."""
from pymongo.errors import PyMongoError
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from .. import database as dbx
from . import interests

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
    """Gợi ý kết bạn = bạn của bạn bè + người cùng chủ đề quan tâm (Neo4j), làm giàu hồ sơ (MongoDB).

    User mới chưa có bạn vẫn có gợi ý nhờ phần chủ đề: đăng/xem/thích/bình luận bài viết.
    """
    try:
        with dbx.neo4j_driver.session() as s:
            res = s.run(
                """MATCH (me:User {id:$id})-[:FRIEND]->()-[:FRIEND]->(fof:User)
                   WHERE fof.id <> $id AND NOT (me)-[:FRIEND]->(fof)
                   RETURN fof.id AS id, count(*) AS mutual
                   ORDER BY mutual DESC LIMIT $limit""",
                id=user_id, limit=limit,
            )
            fof = {r["id"]: r["mutual"] for r in res}
        similar = {s["user_id"]: s for s in interests.similar_users(user_id, limit)}
    except (Neo4jError, ServiceUnavailable, OSError):
        return {**GRAPH_DOWN, "suggestions": []}

    cands = []
    for uid in fof.keys() | similar.keys():
        sim = similar.get(uid, {})
        cands.append({
            "user_id": uid,
            "mutual_friends": fof.get(uid, 0),
            "interest_score": sim.get("interest_score", 0),
            "common_topics": sim.get("common_topics", []),
            "content_match": sim.get("content_match", False),
            "reason": "both" if uid in fof and sim else ("friends" if uid in fof else "interests"),
        })
    # Trùng nội dung trực tiếp xếp trước; sau đó bạn chung + độ trùng chủ đề (đã chuẩn hóa 0-5)
    cands.sort(key=lambda c: (c["content_match"], c["mutual_friends"] + c["interest_score"]), reverse=True)
    cands = cands[:limit]

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
