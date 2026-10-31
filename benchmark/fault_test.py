"""Thí nghiệm mất nút trên cụm giả lập (deploy/local-4pc), gọi qua API thật.

Cần cụm + API đang chạy. Dữ liệu thử được tự xóa khi kết thúc.
Chạy: python benchmark/fault_test.py
"""
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import PyMongoError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend-python"))

from app import database as dbx  # noqa: E402

API = "http://127.0.0.1:8000"
CLUSTER = str(ROOT / "deploy" / "local-4pc" / "cluster.ps1")
REPLICA_SETS = {
    "rs1": "127.0.1.2:27018,127.0.1.3:27028,127.0.1.4:27038",
    "rs2": "127.0.1.3:27018,127.0.1.2:27029,127.0.1.4:27039",
    "cfgrs": "127.0.1.1:27019,127.0.1.2:27019,127.0.1.3:27019",
}
SCENARIOS = [
    ("Mất secondary rs1 (PC3)", ["pc3-rs1sec"]),
    ("Mất primary rs1 (PC2)", ["pc2-rs1"]),
    ("Mất cả PC2", ["pc2-rs1", "pc2-rs2sec", "pc2-cfg"]),
    ("Mất cả PC3", ["pc3-rs2", "pc3-rs1sec", "pc3-cfg"]),
    ("Mất cả PC1 (config primary)", ["pc1-cfg"]),
    ("Mất 2/3 nút rs1 (quá khả năng chịu lỗi)", ["pc2-rs1", "pc3-rs1sec"]),
]
MARK = "FAULT-TEST"
acked_posts = []
counter = 0


def rs_client(rs):
    return MongoClient(f"mongodb://{REPLICA_SETS[rs]}/?replicaSet={rs}",
                       serverSelectionTimeoutMS=5000)


def node(action, name):
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", CLUSTER, action, name],
                   capture_output=True, check=True)


def call(method, path, body=None):
    req = urllib.request.Request(
        API + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def attempt(label, fn):
    t = time.perf_counter()
    try:
        detail = fn()
        status = "OK  "
    except urllib.error.HTTPError as e:
        detail, status = f"HTTP {e.code}", "FAIL"
    except OSError as e:  # timeout / mất kết nối
        detail, status = type(e).__name__, "FAIL"
    print(f"    {label:<24} {status} {time.perf_counter() - t:5.1f}s  {detail}", flush=True)


def write_post(author):
    doc = call("POST", "/posts", {"author_id": author, "content": f"{MARK} {time.time()}"})
    acked_posts.append(doc["_id"])
    return "đã xác nhận"


def register():
    global counter
    counter += 1
    return call("POST", "/users", {"username": f"faulttest{int(time.time())}{counter}",
                                   "password": "test1234", "full_name": MARK})["sync"]


def probe(authors):
    attempt("đăng nhập", lambda: call("POST", "/users/login",
                                      {"username": "user000", "password": "123456"})["username"])
    attempt("bảng tin", lambda: f"{len(call('GET', f'/social/feed/{authors["rs1"]}')['posts'])} bài")
    for rs, author in authors.items():
        attempt(f"đăng bài lên {rs}", lambda a=author: write_post(a))
    attempt("đăng ký người dùng", register)


def wait_recovered(timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            ok = True
            for rs in REPLICA_SETS:
                states = [m["stateStr"] for m in rs_client(rs).admin.command("replSetGetStatus")["members"]]
                ok = ok and sorted(states) == ["PRIMARY", "SECONDARY", "SECONDARY"]
            if ok:
                return True
        except PyMongoError:
            pass
        time.sleep(2)
    return False


def cleanup():
    db = dbx.mongo_client.get_database(dbx.config.DB_NAME)
    users = [u["_id"] for u in db.users.find({"username": re.compile(r"^faulttest\d+$")}, {"_id": 1})]
    posts = db.posts.delete_many({"content": re.compile(f"^{MARK} ")}).deleted_count
    db.users.delete_many({"_id": {"$in": users}})
    db.outbox.delete_many({"payload.id": {"$in": users}})
    with dbx.neo4j_driver.session() as s:
        s.run("MATCH (u:User) WHERE u.id IN $ids DETACH DELETE u", ids=users).consume()
    # Tắt đột ngột làm bộ đếm nhanh của collStats sai; validate sửa lại cho dashboard
    for rs in ("rs1", "rs2"):
        for coll in ("users", "posts", "comments"):
            rs_client(rs).social.command("validate", coll)
    print(f"Đã xóa dữ liệu thử: {posts} bài, {len(users)} người dùng")


def main():
    authors = {rs: rs_client(rs).social.users.find_one({"username": re.compile("^user0")}, {"_id": 1})["_id"]
               for rs in ("rs1", "rs2")}
    print("== Bình thường")
    probe(authors)
    try:
        for title, nodes in SCENARIOS:
            print(f"== {title}: tắt {', '.join(nodes)}", flush=True)
            for n in nodes:
                node("stop-node", n)
            print("  Ngay sau khi mất nút:")
            probe(authors)
            time.sleep(15)
            print("  Sau 15 giây:")
            probe(authors)
            for n in nodes:
                node("start-node", n)
            print(f"  Phục hồi đủ 3 nút mỗi shard: {wait_recovered()}", flush=True)
    finally:
        for _, nodes in SCENARIOS:
            for n in nodes:
                node("start-node", n)
        wait_recovered()

    print("== Sau khi phục hồi")
    probe(authors)
    db = dbx.mongo_client.get_database(dbx.config.DB_NAME)
    found = db.posts.count_documents({"_id": {"$in": acked_posts}})
    print(f"Bài đã được xác nhận ghi: {len(acked_posts)}, còn trong CSDL: {found}")
    cleanup()
    return 0 if found == len(acked_posts) else 1


if __name__ == "__main__":
    sys.exit(main())
