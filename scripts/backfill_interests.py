"""Dựng sở thích (User)-[:INTERESTED_IN]->(Keyword) trên Neo4j từ toàn bộ bài viết đã có.

Chạy 1 lần sau khi nâng cấp (bài mới được API tự ghi):
    python scripts/backfill_interests.py
Chạy lại không sao, nhưng trọng số của từ khóa có trong bài viết sẽ bị đặt lại theo số bài
(phần cộng thêm từ lượt xem/thích/bình luận trên cùng từ khóa đó bị mất).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend-python"))

from app.services import interests  # noqa: E402

if __name__ == "__main__":
    r = interests.rebuild_from_posts()
    print(f"✔ {r['authors']} tác giả · {r['keywords']} từ khóa · {r['edges']} cạnh INTERESTED_IN")
