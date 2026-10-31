"""Đối chiếu MongoDB và Neo4j: số lượng, phân bố shard, khóa liên kết, friend_count."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend-python"))

from app import database as dbx  # noqa: E402


def main():
    for coll in ("users", "posts", "comments"):
        stats = dbx.db.command("collStats", coll)
        per_shard = {k: v.get("count", 0) for k, v in stats.get("shards", {}).items()}
        print(f"MongoDB {coll}: {dbx.db[coll].count_documents({})} (collStats {per_shard})")

    mongo_users = {u["_id"]: u.get("friend_count", 0) for u in dbx.db.users.find({}, {"friend_count": 1})}
    with dbx.neo4j_driver.session() as s:
        graph_users = {r["id"]: r["c"] for r in s.run(
            "MATCH (u:User) OPTIONAL MATCH (u)-[:FRIEND]->(f) RETURN u.id AS id, count(f) AS c")}
        edges = s.run("MATCH ()-[r:FRIEND]->() RETURN count(r) AS c").single()["c"]
    print(f"Neo4j User: {len(graph_users)}, FRIEND (2 chiều): {edges}")

    only_mongo = set(mongo_users) - set(graph_users)
    only_graph = set(graph_users) - set(mongo_users)
    wrong_count = [u for u in mongo_users.keys() & graph_users.keys() if mongo_users[u] != graph_users[u]]
    print(f"Chỉ có ở MongoDB: {len(only_mongo)}, chỉ có ở Neo4j: {len(only_graph)}, "
          f"friend_count lệch: {len(wrong_count)}")
    sys.exit(1 if only_mongo or only_graph or wrong_count else 0)


if __name__ == "__main__":
    main()
