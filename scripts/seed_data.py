"""Nạp dữ liệu mẫu: users, posts, comments (MongoDB) + friendships (Neo4j).

Chạy trên PC4: python scripts/seed_data.py [số_user] [số_post_mỗi_user]
"""
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend-python"))

from app import database as dbx  # noqa: E402
from app.routers.users import hash_password  # noqa: E402

N_USERS = int(sys.argv[1]) if len(sys.argv) > 1 else 30
POSTS_PER_USER = int(sys.argv[2]) if len(sys.argv) > 2 else 20
DEFAULT_PASSWORD = "123456"  # mật khẩu đăng nhập của mọi user mẫu

FIRST = ["An", "Bình", "Chi", "Dũng", "Hà", "Khánh", "Linh", "Minh", "Nam", "Phương",
         "Quân", "Sơn", "Thảo", "Trang", "Tuấn", "Vy"]
LAST = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Vũ", "Đặng", "Bùi"]
TOPICS = ["du lịch Đà Lạt", "học MongoDB sharding", "cà phê sáng", "chạy bộ",
          "đồ án Neo4j", "ẩm thực Hà Nội", "bóng đá tối qua", "mèo của tôi",
          "deadline môn CSDL nâng cao", "chụp ảnh phong cảnh"]


def main():
    print(f"Seed {N_USERS} users x {POSTS_PER_USER} posts...")
    now = datetime.now(timezone.utc)

    # 0. Tài khoản quản trị (role=admin) - dùng cho dashboard và API /admin
    if not dbx.db.users.find_one({"username": "admin"}):
        admin_id = str(uuid.uuid4())
        dbx.db.users.insert_one({
            "_id": admin_id, "username": "admin", "full_name": "Quản trị viên",
            "avatar_url": "", "password_hash": hash_password("admin123"),
            "role": "admin", "friend_count": 0, "created_at": now,
        })
        with dbx.neo4j_driver.session() as s:
            s.run("MERGE (u:User {id:$id}) SET u.username='admin', u.full_name='Quản trị viên'",
                  id=admin_id)
        print("  ✔ admin / admin123 (role=admin)")

    # 1. Users - ghi cả Mongo lẫn Neo4j (mật khẩu chung: 123456)
    user_ids = []
    pw_hash = hash_password(DEFAULT_PASSWORD)
    for i in range(N_USERS):
        uid = str(uuid.uuid4())
        username = f"user{i:03d}"
        full_name = f"{random.choice(LAST)} {random.choice(FIRST)}"
        dbx.db.users.insert_one({
            "_id": uid, "username": username, "full_name": full_name,
            "avatar_url": "", "password_hash": pw_hash,
            "role": "user", "friend_count": 0, "created_at": now,
        })
        with dbx.neo4j_driver.session() as s:
            s.run("MERGE (u:User {id:$id}) SET u.username=$un, u.full_name=$fn",
                  id=uid, un=username, fn=full_name)
        user_ids.append(uid)
    print(f"  ✔ {N_USERS} users (MongoDB + Neo4j)")

    # 2. Posts + comments - phân tán trên 2 shard theo hash(author_id)
    posts, comments = [], []
    for uid in user_ids:
        for _ in range(POSTS_PER_USER):
            pid = str(uuid.uuid4())
            posts.append({
                "_id": pid, "author_id": uid,
                "content": f"Hôm nay mình {random.choice(TOPICS)}, mọi người thấy sao?",
                "image_urls": [], "likes": random.randint(0, 50),
                "created_at": now - timedelta(minutes=random.randint(0, 60 * 24 * 30)),
            })
            for _ in range(random.randint(0, 3)):
                comments.append({
                    "_id": str(uuid.uuid4()), "post_id": pid,
                    "author_id": random.choice(user_ids),
                    "content": random.choice(["Hay quá!", "Tuyệt vời 👍", "Cho mình theo với", "Đồng ý luôn"]),
                    "created_at": now,
                })
    dbx.db.posts.insert_many(posts)
    if comments:
        dbx.db.comments.insert_many(comments)
    print(f"  ✔ {len(posts)} posts, {len(comments)} comments (sharded)")

    # 3. Friendships - đồ thị ngẫu nhiên có cụm (để demo cộng đồng/gợi ý)
    edges = 0
    with dbx.neo4j_driver.session() as s:
        for i, uid in enumerate(user_ids):
            # kết bạn trong "cụm" lân cận + vài cạnh ngẫu nhiên
            candidates = user_ids[max(0, i - 4):i] + random.sample(user_ids, k=2)
            for other in set(candidates) - {uid}:
                s.run("""MATCH (a:User {id:$a}), (b:User {id:$b})
                         MERGE (a)-[:FRIEND]->(b) MERGE (b)-[:FRIEND]->(a)""",
                      a=uid, b=other)
                edges += 1
        # cập nhật friend_count cache vào Mongo
        for uid in user_ids:
            c = s.run("MATCH (:User {id:$id})-[:FRIEND]->(f) RETURN count(f) AS c",
                      id=uid).single()["c"]
            dbx.db.users.update_one({"_id": uid}, {"$set": {"friend_count": c}})
    print(f"  ✔ ~{edges} quan hệ bạn bè (Neo4j)")
    print("HOÀN TẤT. Mở web PHP hoặc chạy benchmark/benchmark.py")


if __name__ == "__main__":
    main()
