"""Khởi tạo cụm giả lập 4 máy (bản Python của init_cluster.ps1, không cần mongosh).

python scripts/init_cluster_local.py replicasets   # cfgrs, rs1, rs2
python scripts/init_cluster_local.py shards        # addShard + shardCollection qua mongos
Chạy lại nhiều lần không sao. Được gọi từ deploy/local-4pc/cluster.ps1.
"""
import sys
import time

from pymongo import MongoClient
from pymongo.errors import OperationFailure, PyMongoError

PC1, PC2, PC3, PC4 = "127.0.1.1", "127.0.1.2", "127.0.1.3", "127.0.1.4"

REPLICA_SETS = [
    (f"{PC1}:27019", {"_id": "cfgrs", "configsvr": True,
                      "members": [{"_id": 0, "host": f"{PC1}:27019", "priority": 2},
                                  {"_id": 1, "host": f"{PC2}:27019", "priority": 1},
                                  {"_id": 2, "host": f"{PC3}:27019", "priority": 1}]}),
    (f"{PC2}:27018", {"_id": "rs1", "members": [
        {"_id": 0, "host": f"{PC2}:27018", "priority": 2},
        {"_id": 1, "host": f"{PC3}:27028", "priority": 1},
        {"_id": 2, "host": f"{PC4}:27038", "priority": 0}]}),
    (f"{PC3}:27018", {"_id": "rs2", "members": [
        {"_id": 0, "host": f"{PC3}:27018", "priority": 2},
        {"_id": 1, "host": f"{PC2}:27029", "priority": 1},
        {"_id": 2, "host": f"{PC4}:27039", "priority": 0}]}),
]
SHARDED = {"posts": "author_id", "comments": "post_id", "users": "_id"}


def init_replica_sets():
    for host, conf in REPLICA_SETS:
        client = MongoClient(f"mongodb://{host}/?directConnection=true",
                             serverSelectionTimeoutMS=5000)
        try:
            client.admin.command("replSetInitiate", conf)
            print(f"  ✔ {conf['_id']} khởi tạo tại {host}")
        except OperationFailure as e:
            if e.code != 23:  # AlreadyInitialized
                raise
            print(f"  - {conf['_id']} đã có sẵn")
        for _ in range(60):
            if client.admin.command("hello").get("isWritablePrimary"):
                break
            time.sleep(1)
        else:
            raise RuntimeError(f"{conf['_id']}: không bầu được primary")
        add_missing_members(conf)


def add_missing_members(conf):
    """Cụm tạo trước đây chỉ có 2 nút: thêm nút còn thiếu (từng nút một) và chờ sao chép xong."""
    hosts = ",".join(m["host"] for m in conf["members"])
    client = MongoClient(f"mongodb://{hosts}/?replicaSet={conf['_id']}",
                         serverSelectionTimeoutMS=30000)
    for member in conf["members"]:
        current = client.admin.command("replSetGetConfig")["config"]
        if any(m["host"] == member["host"] for m in current["members"]):
            continue
        current["members"].append({**member, "_id": max(m["_id"] for m in current["members"]) + 1})
        current["version"] += 1
        client.admin.command("replSetReconfig", current)
        print(f"  ✔ {conf['_id']} thêm {member['host']}, đang sao chép dữ liệu...")
        for _ in range(120):
            states = {m["name"]: m["stateStr"] for m in client.admin.command("replSetGetStatus")["members"]}
            if states.get(member["host"]) == "SECONDARY":
                break
            time.sleep(1)
        else:
            raise RuntimeError(f"{member['host']}: chưa sao chép xong")


def init_shards():
    client = MongoClient(f"mongodb://{PC4}:27017", serverSelectionTimeoutMS=30000)
    existing = {s["_id"] for s in client.admin.command("listShards")["shards"]}
    for rs, host in (("rs1", f"{PC2}:27018"), ("rs2", f"{PC3}:27018")):
        if rs not in existing:
            client.admin.command("addShard", f"{rs}/{host}", name=rs)
        print(f"  ✔ shard {rs}")
    client.admin.command("enableSharding", "social")
    for coll, key in SHARDED.items():
        client.admin.command("shardCollection", f"social.{coll}", key={key: "hashed"})
        print(f"  ✔ social.{coll} shard theo hashed({key})")


def shutdown_all():
    """Tắt đúng quy trình để MongoDB ghi checkpoint (kill -Force làm collStats đếm sai)."""
    hosts = [f"{PC4}:27017", f"{PC4}:27038", f"{PC4}:27039", f"{PC2}:27029", f"{PC3}:27028",
             f"{PC2}:27018", f"{PC3}:27018", f"{PC2}:27019", f"{PC3}:27019", f"{PC1}:27019"]
    for host in hosts:
        client = MongoClient(f"mongodb://{host}/?directConnection=true",
                             serverSelectionTimeoutMS=2000)
        try:
            client.admin.command("shutdown", 1, force=True)
        except PyMongoError:
            pass  # kết nối bị đóng khi nút tắt, hoặc nút đã tắt sẵn


if __name__ == "__main__":
    try:
        {"replicasets": init_replica_sets, "shards": init_shards,
         "shutdown": shutdown_all}[sys.argv[1]]()
    except (PyMongoError, RuntimeError) as e:
        sys.exit(f"LỖI: {e}")
