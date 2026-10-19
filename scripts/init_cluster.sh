#!/usr/bin/env bash
# Khởi tạo MongoDB Sharded Cluster - chạy trên PC4 (bản Linux/macOS, tương đương init_cluster.ps1)
set -e
source "$(dirname "$0")/../.env"

echo "==> 1. Khởi tạo config replica set (cfgrs) trên PC1"
mongosh --host "$PC1_IP" --port 27019 --eval "
rs.initiate({ _id: 'cfgrs', configsvr: true,
  members: [ { _id: 0, host: '$PC1_IP:27019' } ] })"

echo "==> 2. Khởi tạo rs1 (Shard 1: primary PC2, secondary PC3)"
mongosh --host "$PC2_IP" --port 27018 --eval "
rs.initiate({ _id: 'rs1', members: [
  { _id: 0, host: '$PC2_IP:27018', priority: 2 },
  { _id: 1, host: '$PC3_IP:27028', priority: 1 } ] })"

echo "==> 3. Khởi tạo rs2 (Shard 2: primary PC3, secondary PC2)"
mongosh --host "$PC3_IP" --port 27018 --eval "
rs.initiate({ _id: 'rs2', members: [
  { _id: 0, host: '$PC3_IP:27018', priority: 2 },
  { _id: 1, host: '$PC2_IP:27029', priority: 1 } ] })"

echo "==> Chờ 20s cho các replica set bầu primary..."
sleep 20
echo "==> NHỚ: khởi động mongos trên PC4 trước bước 4!"

echo "==> 4. Thêm shard + bật sharding cho DB 'social'"
mongosh --host "$PC4_IP" --port 27017 --eval "
sh.addShard('rs1/$PC2_IP:27018');
sh.addShard('rs2/$PC3_IP:27018');
sh.enableSharding('social');
sh.shardCollection('social.posts',    { author_id: 'hashed' });
sh.shardCollection('social.comments', { post_id: 'hashed' });
sh.shardCollection('social.users',    { _id: 'hashed' });
sh.status();
"
echo "==> HOÀN TẤT."
