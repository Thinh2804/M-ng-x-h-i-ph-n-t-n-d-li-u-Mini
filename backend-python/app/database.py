"""Kết nối MongoDB (qua mongos) và Neo4j, kèm health-check từng nút."""
from pymongo import MongoClient
from pymongo.read_preferences import ReadPreference
from pymongo.errors import PyMongoError
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from . import config

# --- MongoDB: client duy nhất trỏ vào mongos (PC4) ---
mongo_client = MongoClient(
    config.MONGO_URI,
    serverSelectionTimeoutMS=config.MONGO_TIMEOUT_MS,
    connectTimeoutMS=config.MONGO_TIMEOUT_MS,
)
# primaryPreferred: bình thường đọc primary (dữ liệu mới nhất), primary mất thì đọc secondary
db = mongo_client.get_database(
    config.DB_NAME, read_preference=ReadPreference.PRIMARY_PREFERRED
)

# Handle đọc từ secondary - minh họa đọc khi primary chết
db_secondary = mongo_client.get_database(
    config.DB_NAME, read_preference=ReadPreference.SECONDARY_PREFERRED
)

# --- Neo4j (PC4 - Neo4j Desktop) ---
neo4j_driver = GraphDatabase.driver(
    config.NEO4J_URI,
    auth=(config.NEO4J_USER, config.NEO4J_PASSWORD),
    connection_timeout=config.NEO4J_TIMEOUT_S,
)


def mongo_healthy() -> bool:
    try:
        mongo_client.admin.command("ping")
        return True
    except PyMongoError:
        return False


def neo4j_healthy() -> bool:
    try:
        neo4j_driver.verify_connectivity()
        return True
    except (Neo4jError, ServiceUnavailable, OSError):
        return False


def shard_status() -> dict:
    """Trạng thái từng shard/nút - dùng cho dashboard admin."""
    try:
        res = mongo_client.admin.command("listShards")
        shards = [
            {"id": s["_id"], "host": s["host"], "state": s.get("state", 1)}
            for s in res.get("shards", [])
        ]
        return {"ok": True, "shards": shards}
    except PyMongoError as e:
        return {"ok": False, "error": str(e), "shards": []}
