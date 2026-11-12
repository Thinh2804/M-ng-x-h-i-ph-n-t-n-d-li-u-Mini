"""Benchmark phân tán dữ liệu - nhìn từ Shard 2 (rs2, PC3).

Ghi N bài thử nghiệm qua mongos vào collection tạm `bench_posts` (shard theo hashed(author_id)
giống `posts`), rồi:
  1. Đo thông lượng ghi qua mongos
  2. Kết nối THẲNG vào Shard 1 (PC2) và Shard 2 (PC3) đếm số document mỗi shard đang giữ
  3. explain(): truy vấn có shard key chỉ chạm 1 shard, không có shard key chạm mọi shard
  4. Đo thời gian targeted vs scatter-gather
Cuối cùng xóa collection tạm (thêm --keep để giữ lại).

    python benchmark/shard_distribution.py [N] [--keep]
"""
import os
import sys
import time
import uuid
import random
import statistics
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient, InsertOne

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
MONGOS = os.getenv("MONGO_URI", "mongodb://127.0.1.4:27017")
LABELS = {"rs1": "rs1 (Shard 1 - PC2)", "rs2": "rs2 (Shard 2 - PC3)"}
COLL = "bench_posts"
N = int(next((a for a in sys.argv[1:] if a.isdigit()), 5000))
KEEP = "--keep" in sys.argv
AUTHORS = 500
BATCH = 500


def timed(fn, runs=30):
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    return statistics.mean(times), statistics.median(times), sorted(times)[int(runs * 0.95) - 1]


def shards_hit(explain):
    """Tên các shard mà mongos gửi truy vấn tới, lấy từ explain()."""
    winning = explain["queryPlanner"]["winningPlan"]
    return sorted(s["shardName"] for s in winning.get("shards", []))


def main():
    mongos = MongoClient(MONGOS, serverSelectionTimeoutMS=8000)
    db = mongos.social
    # Địa chỉ từng shard lấy từ chính cụm (listShards), dạng "rs2/host1,host2,host3"
    shard_hosts = {s["_id"]: s["host"].split("/", 1)[1] for s in mongos.admin.command("listShards")["shards"]}
    db[COLL].drop()
    mongos.admin.command("shardCollection", f"social.{COLL}", key={"author_id": "hashed"})

    authors = [str(uuid.uuid4()) for _ in range(AUTHORS)]
    print(f"\n{'=' * 78}\nGHI {N} bài thử nghiệm qua mongos {'%s:%d' % mongos.address}\n{'=' * 78}")
    t0 = time.perf_counter()
    for start in range(0, N, BATCH):
        db[COLL].bulk_write([InsertOne({
            "_id": str(uuid.uuid4()), "author_id": random.choice(authors),
            "content": f"bench post {i}", "likes": random.randint(0, 50),
            "created_at": datetime.now(timezone.utc),
        }) for i in range(start, min(start + BATCH, N))], ordered=False)
    secs = time.perf_counter() - t0
    print(f"Thời gian ghi: {secs:.2f}s  →  {N / secs:,.0f} doc/s")

    print(f"\n--- Số document trên từng shard (kết nối thẳng vào primary của shard) ---")
    counts = {}
    for rs, hosts in sorted(shard_hosts.items()):
        c = MongoClient(hosts, replicaSet=rs, serverSelectionTimeoutMS=8000)
        primary = "%s:%d" % c.primary if c.admin.command("ping") and c.primary else "?"
        counts[rs] = c.social[COLL].count_documents({})
        n_auth = len(c.social[COLL].distinct("author_id"))
        print(f"{LABELS.get(rs, rs):<22} {primary:<17} {counts[rs]:>6} doc ({counts[rs] / N:6.1%})  {n_auth} tác giả")
    total = sum(counts.values())
    print(f"{'Tổng':<22} {'':<17} {total:>6} doc  {'(khớp mongos)' if total == db[COLL].count_documents({}) else '(LỆCH với mongos!)'}")

    chunks = list(mongos.config.chunks.aggregate([
        {"$lookup": {"from": "collections", "localField": "uuid", "foreignField": "uuid", "as": "c"}},
        {"$match": {"c._id": f"social.{COLL}"}},
        {"$group": {"_id": "$shard", "n": {"$sum": 1}}}, {"$sort": {"_id": 1}},
    ]))
    print("Chunk: " + ", ".join(f"{c['_id']}={c['n']}" for c in chunks))

    # Tìm 1 tác giả có bài nằm trên Shard 2 để chứng minh targeted query
    rs2 = MongoClient(shard_hosts["rs2"], replicaSet="rs2", serverSelectionTimeoutMS=8000)
    author_on_rs2 = rs2.social[COLL].find_one()["author_id"]

    print(f"\n--- explain(): mongos gửi truy vấn tới shard nào? ---")
    q_target = {"author_id": author_on_rs2}
    q_scatter = {"likes": {"$gte": 40}}
    print(f"Có shard key  {{author_id: <tác giả trên rs2>}} → {shards_hit(db.command('explain', {'find': COLL, 'filter': q_target}))}")
    print(f"Không shard key {{likes >= 40}}                  → {shards_hit(db.command('explain', {'find': COLL, 'filter': q_scatter}))}")

    print(f"\n--- Thời gian truy vấn (30 lần) ---")
    print(f"{'Loại':<42} {'avg(ms)':>9} {'med(ms)':>9} {'p95(ms)':>9}")
    for label, fn in [
        ("Targeted (1 shard - rs2)", lambda: list(db[COLL].find(q_target))),
        ("Scatter-gather (mọi shard)", lambda: list(db[COLL].find(q_scatter).limit(50))),
        ("Aggregate đếm theo tác giả (mọi shard)", lambda: list(db[COLL].aggregate([
            {"$group": {"_id": "$author_id", "n": {"$sum": 1}}}, {"$sort": {"n": -1}}, {"$limit": 10}]))),
    ]:
        avg, med, p95 = timed(fn)
        print(f"{label:<42} {avg:>9.2f} {med:>9.2f} {p95:>9.2f}")

    if KEEP:
        print(f"\nGiữ lại social.{COLL} (--keep).")
    else:
        db[COLL].drop()
        print(f"\nĐã xóa collection tạm social.{COLL}.")


if __name__ == "__main__":
    main()
