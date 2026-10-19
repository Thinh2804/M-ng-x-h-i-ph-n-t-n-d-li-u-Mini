# Mạng Xã Hội Mini – MongoDB Sharded Cluster + Neo4j

Hệ thống CSDL đa mô hình phân tán trên **4 máy cá nhân** (mỗi máy do 1 thành viên quản lý), triển khai **native trên Windows 10/11** theo quy trình 8 giai đoạn.

## 4 sản phẩm cần hoàn thành

1. **Website mạng xã hội mini**: đăng nhập, hồ sơ người dùng, đăng bài, bình luận, thích bài viết, kết bạn, gợi ý bạn bè.
2. **MongoDB Sharded Cluster**: phân phối bài viết/nội dung giữa các shard, minh chứng bằng lệnh và kết quả truy vấn.
3. **Neo4j Graph Database**: nút người dùng + quan hệ bạn bè, truy vấn bạn chung và gợi ý kết nối.
4. **Báo cáo thực nghiệm**: đo thời gian truy vấn, kiểm tra đồng bộ, thử mất kết nối một nút → [docs/EVALUATION.md](docs/EVALUATION.md).

## Phân công dịch vụ cho các máy

| Máy | Dịch vụ chính | Cổng | Thư mục |
|-----|---------------|------|---------|
| **PC1** | Config Server (cfgrs) | 27019 | [deploy/pc1-configsvr](deploy/pc1-configsvr) |
| **PC2** | Shard 1 (rs1 primary) + secondary rs2* | 27018, 27029 | [deploy/pc2-shard1](deploy/pc2-shard1) |
| **PC3** | Shard 2 (rs2 primary) + secondary rs1* | 27018, 27028 | [deploy/pc3-shard2](deploy/pc3-shard2) |
| **PC4 (Master)** | mongos + Python API + PHP Web + Neo4j | 27017, 8000, 8080, 7687 | [deploy/pc4-master](deploy/pc4-master) |

\* Secondary chéo máy để minh họa cơ chế sao chép (replication) – yêu cầu của báo cáo thực nghiệm.

```
                 ┌─────────────── PC4 (MASTER) ────────────────┐
 Người dùng ───▶ │ PHP Web :8080 ─▶ Python API :8000           │
                 │        │               │                    │
                 │        ▼               ▼                    │
                 │  mongos :27017    Neo4j :7687 (Desktop)     │
                 └───────┬──────────────────────────────────── ┘
                         │ configdb
            ┌────────────┼─────────────────┐
            ▼            ▼                 ▼
          PC1          PC2               PC3
     Config :27019  Shard1 :27018    Shard2 :27018
                    rs2-sec :27029   rs1-sec :27028
```

## Phần mềm cần cài đặt

| Phần mềm | Công dụng | Máy cần cài |
|---|---|---|
| Visual Studio Code | Viết chương trình | Máy lập trình |
| Python 3.11+ | Chạy backend FastAPI | PC4 |
| PHP 8+ | Chạy website | PC4 |
| MongoDB Community Server | Tiến trình `mongod`/`mongos` | PC1–PC4 |
| MongoDB Shell (mongosh) | Cấu hình cluster | PC4 (máy quản trị) |
| MongoDB Compass | Xem collection, dữ liệu | PC4 (máy quản trị) |
| Neo4j Desktop | CSDL đồ thị | PC4 |
| Git | Quản lý mã nguồn nhóm | Mọi thành viên |
| Postman | Kiểm tra API | Máy lập trình |

## Các giai đoạn triển khai

### Giai đoạn 1 – Cấu hình mạng (tất cả các máy)
- Kết nối cùng mạng LAN, đặt IP tĩnh (hoặc hostname ổn định).
- Copy `.env.example` → `.env`, điền IP thật của 4 máy.
- Mở firewall **chỉ trong mạng nội bộ** các cổng: `27017-27019, 27028, 27029, 7474, 7687, 8000, 8080`. Không mở MongoDB ra Internet.
- Kiểm tra liên lạc: `ping <IP máy khác>`.

### Giai đoạn 2 – Khởi động dịch vụ MongoDB trên từng máy
```powershell
# PC1 (PowerShell - Administrator)
.\deploy\pc1-configsvr\start_configsvr.ps1
# PC2
.\deploy\pc2-shard1\start_shard1.ps1
# PC3
.\deploy\pc3-shard2\start_shard2.ps1
```

### Giai đoạn 3 – Khởi tạo replica sets (chạy trên PC4, cần mongosh)
```powershell
powershell -File scripts\init_cluster.ps1
# Script tự dừng chờ: khởi động mongos trên PC4 trước bước 4
.\deploy\pc4-master\start_mongos.ps1    # chạy ở cửa sổ khác
```
Script thực hiện: khởi tạo `cfgrs` → `rs1` → `rs2` → `addShard` → bật sharding DB `social` → shard key `hashed(author_id)` cho posts, `hashed(post_id)` cho comments.

### Giai đoạn 4 – Cài Neo4j Desktop trên PC4
Xem hướng dẫn chi tiết: [deploy/pc4-master/NEO4J_SETUP.md](deploy/pc4-master/NEO4J_SETUP.md).

### Giai đoạn 5 – Chạy backend (PC4)
```powershell
cd backend-python
pip install -r requirements.txt
.\..\deploy\pc4-master\start_backend.ps1   # chạy cả Python API + PHP web
```
API docs: `http://<PC4_IP>:8000/docs` — Web: `http://<PC4_IP>:8080`.

### Giai đoạn 6 – Nạp dữ liệu mẫu
```powershell
python scripts\seed_data.py 30 20
# Tạo 30 users (mật khẩu: 123456), 600 posts phân tán 2 shard, quan hệ bạn bè Neo4j
```

### Giai đoạn 7 – Kiểm thử đánh giá
```powershell
python benchmark\benchmark.py
```
Đo: truy vấn targeted vs scatter-gather, đọc primary vs secondary, truy vấn liên mô hình, replication lag. Thí nghiệm mất kết nối nút: xem [docs/EVALUATION.md](docs/EVALUATION.md).

### Giai đoạn 8 – Viết báo cáo
Dùng số liệu từ benchmark + ảnh chụp dashboard giám sát (`http://<PC4_IP>:8080/index.php?page=admin`) và `sh.status()` làm minh chứng.

## Tính năng phân tán đã cài đặt

1. **Truy vấn/giao dịch trên nhiều nút**: mongos định tuyến targeted (có shard key) hoặc scatter-gather; ghi `w=majority`.
2. **Kết hợp 2 mô hình**: News Feed = Neo4j (bạn bè) → MongoDB (`$in` bài viết); Gợi ý kết bạn = Cypher friend-of-friend + hồ sơ/số bài từ MongoDB.
3. **Đồng bộ liên CSDL**: tạo user dual-write MongoDB → Neo4j theo mẫu **Saga + Outbox** ([sync.py](backend-python/app/services/sync.py)) — Neo4j chết thì rollback hoặc retry tự động.
4. **Chịu lỗi nút**: đọc `secondaryPreferred` sống sót khi primary chết; Neo4j chết → website chuyển chế độ degraded, feed vẫn hoạt động.
