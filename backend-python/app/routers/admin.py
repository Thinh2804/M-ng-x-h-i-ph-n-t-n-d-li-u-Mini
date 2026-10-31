"""API admin - trạng thái cluster, phân bố shard, outbox, benchmark.

Phân quyền: mọi endpoint yêu cầu header X-User-Id của user có role='admin'.
"""
import time
import statistics

from fastapi import APIRouter, Depends, Header, HTTPException
from pymongo.errors import PyMongoError
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from .. import database as dbx
from ..services import sync


def require_admin(x_user_id: str | None = Header(default=None)):
    """Dependency kiểm tra quyền admin qua header X-User-Id."""
    if not x_user_id:
        raise HTTPException(401, "Thiếu header X-User-Id - hãy đăng nhập")
    u = dbx.db.users.find_one({"_id": x_user_id}, {"role": 1})
    if not u:
        raise HTTPException(401, "User không tồn tại")
    if u.get("role") != "admin":
        raise HTTPException(403, "Chỉ admin được truy cập API quản trị")
    return u


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/health")
def health():
    """Trạng thái từng nút - PHP dashboard gọi endpoint này."""
    return {
        "mongo_cluster": dbx.mongo_healthy(),
        "neo4j": dbx.neo4j_healthy(),
        "shards": dbx.shard_status(),
        "outbox_pending": _outbox_pending(),
    }


def _outbox_pending() -> int:
    try:
        return dbx.db.outbox.count_documents({"status": "pending"})
    except PyMongoError:
        return -1


@router.get("/shard-distribution")
def shard_distribution():
    """Số document của mỗi collection trên từng shard - minh họa phân mảnh."""
    out = {}
    for coll in ("posts", "comments", "users"):
        try:
            stats = dbx.db.command("collStats", coll)
            out[coll] = {
                "total": stats.get("count", 0),
                "per_shard": {
                    shard: s.get("count", 0)
                    for shard, s in stats.get("shards", {}).items()
                },
            }
        except PyMongoError as e:
            out[coll] = {"error": str(e)}
    return out


@router.get("/sync-view")
def sync_view():
    """Đặt cạnh nhau dữ liệu từng user ở MongoDB và Neo4j, nối qua users._id = User.id."""
    mongo = {
        u["_id"]: u
        for u in dbx.db.users.find({}, {"username": 1, "full_name": 1, "friend_count": 1})
    }
    posts = {
        r["_id"]: r["n"]
        for r in dbx.db.posts.aggregate([{"$group": {"_id": "$author_id", "n": {"$sum": 1}}}])
    }
    try:
        with dbx.neo4j_driver.session() as s:
            graph = {
                r["id"]: r
                for r in s.run(
                    """MATCH (u:User) OPTIONAL MATCH (u)-[:FRIEND]->(f:User)
                       RETURN u.id AS id, u.username AS username, u.full_name AS full_name,
                              count(f) AS friends"""
                ).data()
            }
    except (Neo4jError, ServiceUnavailable, OSError):
        return {"neo4j_ok": False, "rows": [], "outbox_pending": _outbox_pending()}

    rows = []
    for uid in mongo.keys() | graph.keys():
        m, g = mongo.get(uid), graph.get(uid)
        synced = bool(m and g and m.get("username") == g["username"]
                      and m.get("full_name", "") == g["full_name"]
                      and m.get("friend_count", 0) == g["friends"])
        rows.append({
            "id": uid, "synced": synced, "mongo": m, "neo4j": g,
            "posts": posts.get(uid, 0),
        })
    rows.sort(key=lambda r: (r["mongo"] or r["neo4j"])["username"])
    return {"neo4j_ok": True, "rows": rows, "outbox_pending": _outbox_pending()}


@router.post("/outbox/process")
def process_outbox():
    return {"processed": sync.process_outbox_once()}


@router.get("/benchmark")
def benchmark(runs: int = 20):
    """So sánh targeted (có shard key) vs scatter-gather (không shard key)."""
    sample = dbx.db.posts.find_one()
    if not sample:
        return {"error": "Chưa có dữ liệu - chạy scripts/seed_data.py trước"}
    author = sample["author_id"]

    def measure(fn):
        times = []
        for _ in range(runs):
            t0 = time.perf_counter()
            fn()
            times.append((time.perf_counter() - t0) * 1000)
        return {
            "avg_ms": round(statistics.mean(times), 2),
            "p95_ms": round(sorted(times)[int(runs * 0.95) - 1], 2),
            "min_ms": round(min(times), 2),
        }

    return {
        "runs": runs,
        "targeted_query (1 shard, theo shard key)": measure(
            lambda: list(dbx.db.posts.find({"author_id": author}).limit(20))
        ),
        "scatter_gather (mọi shard, regex)": measure(
            lambda: list(dbx.db.posts.find({"content": {"$regex": "a"}}).limit(20))
        ),
        "secondary_read (đọc từ secondary chéo máy)": measure(
            lambda: list(dbx.db_secondary.posts.find({"author_id": author}).limit(20))
        ),
    }
