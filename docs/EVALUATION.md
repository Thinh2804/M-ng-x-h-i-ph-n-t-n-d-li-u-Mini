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
Hoặc xem dashboard: `http://<PC4_IP>:8080/admin.php` (giao diện cũ: `http://<PC4_IP>:8081/index.php?page=admin`).

## 3. Minh họa cơ chế sao chép / đồng bộ

### 3.1 Replication trong MongoDB (rs1, rs2 – chéo máy PC2↔PC3)
- rs1: primary PC2:27018 → secondary PC3:27028, PC4:27038; rs2: primary PC3:27018 → secondary PC2:27029, PC4:27039. Bản sao trên PC4 có priority 0 (không làm primary), giúp mỗi shard còn đa số 2/3 khi mất 1 máy.
- `benchmark.py` đo **replication lag**: ghi vào primary rồi poll secondary → thường **< 50ms** trên LAN.
- Ghi với `w=majority` (trong `MONGO_URI`) đảm bảo dữ liệu nằm trên ≥ 2 máy trước khi ack.
- Kiểm chứng bằng mongosh: `rs.status()` trên PC2/PC3 xem `optimeDate` của từng thành viên.

### 3.2 Đồng bộ liên mô hình MongoDB ↔ Neo4j (Saga + Outbox)
- Tạo user: ghi Mongo → ghi Neo4j.
  - Neo4j lỗi + chế độ `strong`: **compensation** – xóa lại bản ghi Mongo, trả lỗi 503.
  - Neo4j lỗi + chế độ mặc định: ghi vào collection `outbox`, worker nền retry mỗi 10s → **nhất quán cuối cùng**.
- Kiểm chứng: tắt Neo4j Desktop (PC4) → đăng ký user trên web → dashboard hiện "Outbox chờ: 1" → bật lại Neo4j → sau ≤10s outbox về 0, node `User` xuất hiện trong Neo4j Browser.

## 4. Thí nghiệm mất kết nối một nút

Số đo dưới đây lấy trên **cụm giả lập 4 máy trong 1 máy** (`deploy/local-4pc`, MongoDB 9.0, không có độ trễ mạng thật), gọi qua API thật bằng `benchmark/fault_test.py`. Khi có 4 máy thật, nhóm nên đo lại.

| Kịch bản | Đọc (đăng nhập, bảng tin) | Ghi | Cơ chế |
|---|---|---|---|
| Mất secondary rs1 | Không gián đoạn | Không gián đoạn | Còn đa số 2/3 |
| Mất primary rs1 | Không gián đoạn | Ghi vào rs1 chờ ~14s trong lúc bầu primary, sau đó bình thường; rs2 không ảnh hưởng | Replica set election + `primaryPreferred` |
| Mất cả PC2 hoặc cả PC3 | Vẫn chạy (đăng nhập chậm nhất ~2s) | Lần ghi đầu chờ tối đa ~4s, sau đó bình thường | Mỗi replica set còn 2/3 thành viên |
| Mất PC1 (config primary) | Không gián đoạn | Không gián đoạn | `cfgrs` 3 thành viên, bầu primary mới |
| Mất 2/3 nút rs1 (vượt khả năng chịu lỗi) | Vẫn chạy (đọc từ bản sao còn lại, có thể cũ hơn primary) | Ghi vào rs1 trả 503 sau ~15s; rs2 vẫn ghi được | Không còn đa số nên không bầu được primary |
| Tắt Neo4j trên PC4 | Đăng nhập bình thường; bảng tin chế độ "degraded" (chỉ bài của mình); tính năng bạn bè trả 503 có thông báo rõ | Đăng bài bình thường; đăng ký vào outbox, tự đồng bộ khi Neo4j bật lại | Graceful degradation + outbox |

Kiểm tra độ bền: mọi bài đã được xác nhận ghi (`w=majority`) trong thí nghiệm đều còn sau khi phục hồi (26/26).

**Bài học từ thiết kế ban đầu (mỗi shard 2 nút, 1 config server), đã đo được:**
- Replica set 2 nút không chịu được lỗi: mất **bất kỳ** nút nào, kể cả secondary, primary cũng tự rút xuống vì mất đa số. Đăng nhập và bảng tin lỗi vì đọc từ primary.
- Mất config server duy nhất làm toàn hệ thống lỗi sau ~15s (`could not get updated shard list from config server`). Cache metadata của mongos không đủ để tiếp tục phục vụ.
- Arbiter chỉ giải quyết được bầu primary; khi mất một nút dữ liệu, ghi `w=majority` vẫn không được xác nhận. Vì vậy nhóm chọn bản sao có dữ liệu.

**Giới hạn còn lại:** PC4 vẫn là điểm hỏng duy nhất, vì chỉ có 1 mongos, 1 API, 1 web và 1 Neo4j trên máy này. Mất PC4 thì website ngừng hoạt động.

## 5. Kết luận kỹ thuật

1. **Polyglot persistence hiệu quả**: MongoDB tối ưu tài liệu lớn, ghi nhanh, shard ngang; Neo4j tối ưu truy vấn đa bước trên đồ thị (friend-of-friend chỉ 1 câu Cypher).
2. **Chi phí của phân tán**: truy vấn liên mô hình (feed) = độ trễ Neo4j + Mongo + xử lý ứng dụng — chấp nhận được (~2× truy vấn đơn) đổi lấy khả năng mở rộng.
3. **Điểm yếu cần lưu ý**: mongos, API và Neo4j đơn trên PC4 là điểm hỏng duy nhất (sản xuất thật cần nhiều mongos, nhiều API, Neo4j cluster); outbox chỉ đạt eventual consistency.
4. **Khuyến nghị**: shard key nên là trường xuất hiện trong hầu hết truy vấn (`author_id` cho posts); luôn `w=majority` cho dữ liệu quan trọng; giám sát replication lag và outbox định kỳ.

## 6. Cách tái tạo số liệu

```powershell
python scripts\seed_data.py 30 20      # nạp dữ liệu
python benchmark\benchmark.py          # đo và in bảng
# Thí nghiệm lỗi tự động trên cụm giả lập (tự xóa dữ liệu thử):
python benchmark\fault_test.py
# Thí nghiệm lỗi thủ công trên 4 máy thật:
# - Trên PC2: dừng tiến trình mongod (Ctrl+C hoặc Stop-Process) → chạy lại benchmark
# - Trên PC4: Stop DBMS trong Neo4j Desktop → đăng ký user mới → xem outbox trên dashboard
```
