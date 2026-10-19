"""Benchmark hệ thống phân tán - chạy trên PC4.

Đo và so sánh:
1. Targeted query (có shard key, 1 shard) vs Scatter-gather (mọi shard)
2. Đọc primary vs secondary (chéo máy PC2↔PC3) - minh họa sao chép
3. Truy vấn liên mô hình (Neo4j + MongoDB) vs từng mô hình riêng
4. Độ trễ sao chép (replication lag): ghi primary → đọc secondary

Kết quả in dạng bảng, có thể dán vào báo cáo.
"""
import sys
import time
import uuid
import statistics
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend-python"))

from app import database as dbx                      # noqa: E402
from app.services import social_graph               # noqa: E402

RUNS = 30


def measure(label, fn, runs=RUNS):
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    row = (label, round(statistics.mean(times), 2),
           round(statistics.median(times), 2),
           round(sorted(times)[int(runs * 0.95) - 1], 2))
    print(f"{row[0]:<55} {row[1]:>9} {row[2]:>9} {row[3]:>9}")
    return row


def replication_lag_test():
    """Ghi vào primary, poll secondary tới khi thấy document → đo lag."""
    marker = str(uuid.uuid4())
    t0 = time.perf_counter()
    dbx.db.posts.insert_one({
        "_id": marker, "author_id": "lag-test", "content": "replication probe",
        "image_urls": [], "likes": 0, "created_at": datetime.now(timezone.utc),
    })
    while True:
        if dbx.db_secondary.posts.find_one({"_id": marker}):
            lag = (time.perf_counter() - t0) * 1000
            break
        if time.perf_counter() - t0 > 10:
            lag = -1
            break
        time.sleep(0.005)
    dbx.db.posts.delete_one({"_id": marker})
    return lag


def main():
    sample = dbx.db.posts.find_one({"author_id": {"$ne": "lag-test"}})
    if not sample:
        print("Chưa có dữ liệu - chạy: python scripts/seed_data.py")
        return
    author = sample["author_id"]
    some_user = dbx.db.users.find_one()["_id"]

    print(f"\n{'='*85}\nBENCHMARK - {RUNS} lần/loại truy vấn\n{'='*85}")
    print(f"{'Loại truy vấn':<55} {'avg(ms)':>9} {'med(ms)':>9} {'p95(ms)':>9}")
    print("-" * 85)

    print("\n--- 1. Cục bộ (targeted, 1 shard) vs Phân tán (scatter-gather) ---")
    measure("Targeted: find theo shard key author_id",
            lambda: list(dbx.db.posts.find({"author_id": author}).limit(20)))
    measure("Scatter-gather: regex content trên mọi shard",
            lambda: list(dbx.db.posts.find({"content": {"$regex": "Đà Lạt"}}).limit(20)))
    measure("Scatter-gather: aggregate đếm post theo author",
            lambda: list(dbx.db.posts.aggregate([
                {"$group": {"_id": "$author_id", "n": {"$sum": 1}}},
                {"$sort": {"n": -1}}, {"$limit": 10},
            ])))

    print("\n--- 2. Đọc primary (PC2/PC3) vs secondary (chéo máy PC3/PC2) ---")
    measure("Đọc PRIMARY",
            lambda: list(dbx.db.posts.find({"author_id": author}).limit(20)))
    measure("Đọc SECONDARY (secondaryPreferred)",
            lambda: list(dbx.db_secondary.posts.find({"author_id": author}).limit(20)))

    print("\n--- 3. Một mô hình vs liên mô hình (Neo4j + MongoDB) ---")
    measure("Chỉ MongoDB: posts của 1 user",
            lambda: list(dbx.db.posts.find({"author_id": some_user}).limit(20)))
    measure("Chỉ Neo4j: danh sách bạn bè",
            lambda: social_graph.get_friend_ids(some_user))
    measure("Liên mô hình: news feed (Neo4j → MongoDB $in)",
            lambda: social_graph.news_feed(some_user, 20))
    measure("Liên mô hình: gợi ý kết bạn (FoF + enrich)",
            lambda: social_graph.suggest_friends(some_user, 10), runs=10)

    print("\n--- 4. Độ trễ sao chép primary → secondary ---")
    lags = [replication_lag_test() for _ in range(5)]
    ok = [x for x in lags if x >= 0]
    if ok:
        print(f"Replication lag (5 lần): avg={statistics.mean(ok):.1f}ms, "
              f"max={max(ok):.1f}ms  (bao gồm thời gian poll 5ms/lần)")
    else:
        print("Không đo được lag (secondary không bắt kịp trong 10s)")

    print(f"\n{'='*85}\nGợi ý thí nghiệm chịu lỗi:")
    print("  1. Tắt mongod shard1 (trên PC2) → chạy lại benchmark:")
    print("     - Đọc secondaryPreferred vẫn OK (secondary rs1 trên PC3), ghi fail-over.")
    print("  2. Tắt Neo4j (trên PC4) → feed chuyển chế độ degraded,")
    print("     tạo user mới đi vào outbox, bật lại Neo4j → outbox tự đồng bộ.")


if __name__ == "__main__":
    main()
