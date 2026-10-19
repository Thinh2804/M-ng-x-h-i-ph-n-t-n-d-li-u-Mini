# Đánh giá hoạt động hệ thống (Sản phẩm 4 – Báo cáo thực nghiệm)

## 1. Phương pháp đo

- Công cụ: `benchmark/benchmark.py` (chạy trên PC4), mỗi loại truy vấn chạy 30 lần, lấy avg / median / p95.
- Dữ liệu mẫu: 30 users × 20 posts = 600 posts + ~1200 comments (từ `scripts/seed_data.py`), phân tán trên 2 shard theo `hashed(author_id)`.
- Mạng: LAN 4 máy Windows, MongoDB cài native, Neo4j Desktop trên PC4.
- Kết quả bên dưới là **số liệu mẫu tham khảo** – nhóm thay bằng số đo thật khi chạy.

## 2. So sánh truy vấn cục bộ vs phân tán

| Truy vấn | Loại | avg (ms) | p95 (ms) | Nhận xét |
|---|---|---|---|---|
| `find({author_id})` | **Targeted** – 1 shard | ~2–5 | ~8 | mongos băm shard key → định tuyến đúng 1 shard (PC2 hoặc PC3) |
| `find({content: /regex/})` | **Scatter-gather** – mọi shard | ~8–20 | ~35 | mongos gửi tới **cả 2 shard**, chờ merge → chậm hơn 3–5× |
| `aggregate` group theo author | Scatter-gather + merge | ~15–40 | ~60 | mỗi shard group cục bộ, mongos merge lần cuối |

**Nhận xét kỹ thuật:** chọn shard key đúng với mẫu truy vấn là yếu tố quyết định. Truy vấn chứa shard key có độ trễ gần bằng truy vấn máy đơn; truy vấn không có shard key chịu thêm chi phí fan-out + round-trip mạng tới mọi shard và bước merge tại mongos.

### Minh chứng phân phối dữ liệu giữa các shard
```javascript
// mongosh --host <PC4_IP> --port 27017
sh.status()                                    // chunk phân bố rs1/rs2
db.posts.getShardDistribution()                // % documents mỗi shard
```
Hoặc xem dashboard: `http://<PC4_IP>:8080/index.php?page=admin`.

## 3. Minh họa cơ chế sao chép / đồng bộ

### 3.1 Replication trong MongoDB (rs1, rs2 – chéo máy PC2↔PC3)
- rs1: primary PC2:27018 → secondary PC3:27028; rs2: primary PC3:27018 → secondary PC2:27029.
- `benchmark.py` đo **replication lag**: ghi vào primary rồi poll secondary → thường **< 50ms** trên LAN.
- Ghi với `w=majority` (trong `MONGO_URI`) đảm bảo dữ liệu nằm trên ≥ 2 máy trước khi ack.
- Kiểm chứng bằng mongosh: `rs.status()` trên PC2/PC3 xem `optimeDate` của từng thành viên.

### 3.2 Đồng bộ liên mô hình MongoDB ↔ Neo4j (Saga + Outbox)
- Tạo user: ghi Mongo → ghi Neo4j.
  - Neo4j lỗi + chế độ `strong`: **compensation** – xóa lại bản ghi Mongo, trả lỗi 503.
  - Neo4j lỗi + chế độ mặc định: ghi vào collection `outbox`, worker nền retry mỗi 10s → **nhất quán cuối cùng**.
- Kiểm chứng: tắt Neo4j Desktop (PC4) → đăng ký user trên web → dashboard hiện "Outbox chờ: 1" → bật lại Neo4j → sau ≤10s outbox về 0, node `User` xuất hiện trong Neo4j Browser.

## 4. Thí nghiệm mất kết nối một nút

| Kịch bản | Hành vi quan sát | Cơ chế |
|---|---|---|
| Tắt mongod trên PC2 (shard1 primary) | Đọc vẫn OK (secondaryPreferred → secondary rs1 trên PC3); secondary được bầu làm primary sau ~10s, ghi phục hồi | Replica set election + read preference |
| Tắt Neo4j trên PC4 | Feed chuyển chế độ "degraded", đăng ký user đi vào outbox; tính năng bạn bè trả 503 có thông báo rõ | Graceful degradation + outbox |
| Tắt mongod trên PC3 (shard2 primary) | ~50% posts (thuộc rs2) tạm fail-over; đọc từ secondary rs2 trên PC2 vẫn hoạt động | Sharding cô lập lỗi theo phạm vi dữ liệu |
| Tắt Config Server (PC1) | Cluster vẫn đọc/ghi được tạm thời (mongos cache metadata) nhưng không thể split/migrate chunk; cần khôi phục sớm | Metadata caching tại mongos |

## 5. Kết luận kỹ thuật

1. **Polyglot persistence hiệu quả**: MongoDB tối ưu tài liệu lớn, ghi nhanh, shard ngang; Neo4j tối ưu truy vấn đa bước trên đồ thị (friend-of-friend chỉ 1 câu Cypher).
2. **Chi phí của phân tán**: truy vấn liên mô hình (feed) = độ trễ Neo4j + Mongo + xử lý ứng dụng — chấp nhận được (~2× truy vấn đơn) đổi lấy khả năng mở rộng.
3. **Điểm yếu cần lưu ý**: config server đơn thành viên trên PC1 và mongos đơn trên PC4 là điểm nghẽn (sản xuất thật cần 3 config server + nhiều mongos); outbox chỉ đạt eventual consistency.
4. **Khuyến nghị**: shard key nên là trường xuất hiện trong hầu hết truy vấn (`author_id` cho posts); luôn `w=majority` cho dữ liệu quan trọng; giám sát replication lag và outbox định kỳ.

## 6. Cách tái tạo số liệu

```powershell
python scripts\seed_data.py 30 20      # nạp dữ liệu
python benchmark\benchmark.py          # đo và in bảng
# Thí nghiệm lỗi:
# - Trên PC2: dừng tiến trình mongod (Ctrl+C hoặc Stop-Process) → chạy lại benchmark
# - Trên PC4: Stop DBMS trong Neo4j Desktop → đăng ký user mới → xem outbox trên dashboard
```
