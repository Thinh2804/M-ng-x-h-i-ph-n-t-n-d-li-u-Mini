"""Đồng bộ liên CSDL (MongoDB ↔ Neo4j) theo mẫu Saga + Outbox.

- Tạo user: ghi Mongo trước → ghi Neo4j. Neo4j lỗi → compensate (xóa Mongo)
  hoặc ghi vào outbox để retry sau (chọn qua tham số).
- Outbox: collection `social.outbox`, worker retry định kỳ.
"""
import time
import uuid
import logging
import threading
from datetime import datetime, timezone

from pymongo.errors import PyMongoError, WTimeoutError
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from .. import database as dbx

log = logging.getLogger("sync")


def _now():
    return datetime.now(timezone.utc)


def create_user_dual_write(username: str, full_name: str, avatar_url: str,
                           password_hash: str = "", role: str = "user",
                           use_outbox: bool = True) -> dict:
    """Ghi user vào cả 2 CSDL với đảm bảo nhất quán."""
    user_id = str(uuid.uuid4())
    doc = {
        "_id": user_id, "username": username, "full_name": full_name,
        "avatar_url": avatar_url, "password_hash": password_hash,
        "role": role, "friend_count": 0, "created_at": _now(),
    }
    # Bước 1: MongoDB (w=majority qua URI)
    try:
        dbx.db.users.insert_one(doc)
    except WTimeoutError as e:
        # Đã ghi trên primary nhưng chưa đủ majority: bù lại để không sót user thiếu node Neo4j
        try:
            dbx.db.users.delete_one({"_id": user_id})
        except PyMongoError:
            log.warning("Không xóa được user %s khi bù trừ", user_id)
        raise RuntimeError(f"MongoDB chưa đủ bản sao để xác nhận ghi: {e}") from e

    # Bước 2: Neo4j
    try:
        with dbx.neo4j_driver.session() as s:
            s.run(
                "MERGE (u:User {id: $id}) SET u.username = $username, u.full_name = $fn",
                id=user_id, username=username, fn=full_name,
            )
        return {"status": "ok", "user_id": user_id, "sync": "synced"}
    except (Neo4jError, ServiceUnavailable, OSError) as e:
        if use_outbox:
            # Nhất quán cuối cùng: lưu thao tác chờ retry
            dbx.db.outbox.insert_one({
                "_id": str(uuid.uuid4()), "type": "create_user_node",
                "payload": {"id": user_id, "username": username, "full_name": full_name},
                "created_at": _now(), "retries": 0, "status": "pending",
            })
            log.warning("Neo4j down, user %s đưa vào outbox: %s", user_id, e)
            return {"status": "ok", "user_id": user_id, "sync": "pending_outbox"}
        # Nhất quán mạnh: rollback Mongo (compensation)
        dbx.db.users.delete_one({"_id": user_id})
        raise RuntimeError(f"Neo4j unavailable, đã rollback MongoDB: {e}") from e


def create_friendship_dual(from_user: str, to_user: str) -> dict:
    """Quan hệ bạn bè: nguồn sự thật là Neo4j; Mongo chỉ lưu đếm cache."""
    with dbx.neo4j_driver.session() as s:
        matched = s.run(
            """MATCH (a:User {id: $a}), (b:User {id: $b})
               MERGE (a)-[:FRIEND]->(b) MERGE (b)-[:FRIEND]->(a)
               RETURN count(*) AS c""",
            a=from_user, b=to_user,
        ).single()["c"]
    if not matched:
        # User chưa có node (không tồn tại hoặc còn chờ trong outbox)
        raise LookupError("User chưa có trong Neo4j")
    # Cache số bạn vào Mongo (best-effort, không cần giao dịch)
    try:
        for uid in (from_user, to_user):
            with dbx.neo4j_driver.session() as s:
                rec = s.run(
                    "MATCH (:User {id:$id})-[:FRIEND]->(f) RETURN count(f) AS c", id=uid
                ).single()
            dbx.db.users.update_one({"_id": uid}, {"$set": {"friend_count": rec["c"]}})
    except (PyMongoError, Neo4jError, ServiceUnavailable):
        log.warning("Không cập nhật được friend_count cache (bỏ qua)")
    return {"status": "ok"}


def process_outbox_once() -> int:
    """Retry các thao tác pending trong outbox. Trả về số bản ghi xử lý được."""
    done = 0
    for item in dbx.db.outbox.find({"status": "pending"}).limit(50):
        try:
            if item["type"] == "create_user_node":
                p = item["payload"]
                with dbx.neo4j_driver.session() as s:
                    s.run(
                        "MERGE (u:User {id: $id}) SET u.username = $username, u.full_name = $fn",
                        id=p["id"], username=p["username"], fn=p.get("full_name", ""),
                    )
            elif item["type"] == "record_interest":
                from .interests import write_interest
                p = item["payload"]
                write_interest(p["user_id"], p["keywords"], p["weight"],
                               p.get("target_id"), p.get("find_matches", False))
            dbx.db.outbox.update_one(
                {"_id": item["_id"]},
                {"$set": {"status": "done", "done_at": _now()}},
            )
            done += 1
        except (Neo4jError, ServiceUnavailable, OSError):
            dbx.db.outbox.update_one({"_id": item["_id"]}, {"$inc": {"retries": 1}})
    return done


def start_outbox_worker(interval_s: int = 10):
    """Worker nền retry outbox - khởi động cùng FastAPI."""
    def loop():
        while True:
            try:
                n = process_outbox_once()
                if n:
                    log.info("Outbox: đồng bộ lại %d bản ghi", n)
            except PyMongoError:
                pass
            time.sleep(interval_s)

    t = threading.Thread(target=loop, daemon=True, name="outbox-worker")
    t.start()
    return t
