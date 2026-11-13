# HƯỚNG DẪN TOÀN PHẦN – Mạng Xã Hội Mini (MongoDB Sharded Cluster + Neo4j)

> Tài liệu đầy đủ: kiến trúc → schema dữ liệu → phân quyền → triển khai → test API bằng Postman.

---

## 1. Kiến trúc tổng thể

| Máy | Dịch vụ | Cổng |
|-----|---------|------|
| **PC1** | Config Server (`cfgrs`, ưu tiên primary) | 27019 |
| **PC2** | Shard 1 primary (`rs1`) + secondary rs2 + config server | 27018, 27029, 27019 |
| **PC3** | Shard 2 primary (`rs2`) + secondary rs1 + config server | 27018, 27028, 27019 |
| **PC4 (Master)** | `mongos` + Python API + PHP Web + Neo4j Desktop + bản sao thứ 3 của rs1, rs2 | 27017, 8000, 8080, 7687, 27038, 27039 |

Luồng dữ liệu: **Trình duyệt → PHP (:8080) → Python API (:8000) → mongos (:27017) → Shard PC2/PC3** và **→ Neo4j (:7687)**.

---

## 2. Schema MongoDB (database `social`)

### 2.1 Collection `users` — shard key: `{ _id: "hashed" }`

| Trường | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `_id` | string (UUID) | ✔ | Khóa chính, đồng thời là `id` của node User bên Neo4j |
| `username` | string (2–50) | ✔ | Duy nhất, dùng đăng nhập |
| `password_hash` | string | ✔ | PBKDF2-SHA256, định dạng `salt_hex$hash_hex` (100.000 vòng) |
| `full_name` | string | | Tên hiển thị |
| `avatar_url` | string | | URL ảnh đại diện |
| `role` | string | ✔ | `"user"` hoặc `"admin"` — dùng phân quyền API |
| `friend_count` | int | | **Cache** từ Neo4j (denormalized, cập nhật khi kết bạn) |
| `created_at` | ISODate | ✔ | Thời điểm tạo |

### 2.2 Collection `posts` — shard key: `{ author_id: "hashed" }`

| Trường | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `_id` | string (UUID) | ✔ | Khóa chính |
| `author_id` | string | ✔ | **Shard key** — tham chiếu `users._id`; truy vấn theo trường này là *targeted* (1 shard) |
| `content` | string (1–5000) | ✔ | Nội dung bài viết |
| `image_urls` | array\<string\> | | Danh sách URL hình ảnh (metadata, ảnh lưu ngoài) |
| `likes` | int | ✔ | Số lượt thích, tăng bằng `$inc` (atomic) |
| `created_at` | ISODate | ✔ | Dùng sort bảng tin |

### 2.3 Collection `comments` — shard key: `{ post_id: "hashed" }`

| Trường | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `_id` | string (UUID) | ✔ | Khóa chính |
| `post_id` | string | ✔ | **Shard key** — bình luận cùng bài nằm cùng shard với nhau |
| `author_id` | string | ✔ | Người bình luận |
| `content` | string (1–2000) | ✔ | Nội dung |
| `created_at` | ISODate | ✔ | Sort tăng dần khi hiển thị |

### 2.4 Collection `outbox` — không shard (đồng bộ liên CSDL)

| Trường | Kiểu | Mô tả |
|---|---|---|
| `_id` | string (UUID) | Khóa chính |
| `type` | string | Loại thao tác chờ retry, vd `"create_user_node"` |
| `payload` | object | Dữ liệu cần ghi sang Neo4j |
| `status` | string | `"pending"` → `"done"` |
| `retries` | int | Số lần thử lại |
| `created_at` / `done_at` | ISODate | Thời điểm tạo / hoàn tất |

### 2.5 Lệnh tạo index + sharding (đã nằm trong `scripts/init_cluster.ps1`)

```javascript
sh.enableSharding('social');
sh.shardCollection('social.posts',    { author_id: 'hashed' });
sh.shardCollection('social.comments', { post_id: 'hashed' });
sh.shardCollection('social.users',    { _id: 'hashed' });
// Index bổ sung nên tạo (chạy 1 lần qua mongos):
db.users.createIndex({ username: 1 }, { unique: true });
db.posts.createIndex({ author_id: 1, created_at: -1 });
db.comments.createIndex({ post_id: 1, created_at: 1 });
db.outbox.createIndex({ status: 1 });
```

---

## 3. Schema Neo4j (đồ thị xã hội)

### 3.1 Node `User`

| Thuộc tính | Kiểu | Mô tả |
|---|---|---|
| `id` | string | **= `users._id` bên MongoDB** (khóa liên kết 2 CSDL) |
| `username` | string | Sao chép để hiển thị nhanh trong Browser |
| `full_name` | string | Tên hiển thị |

### 3.2 Relationship `FRIEND`

- `(:User)-[:FRIEND]->(:User)` — tạo **2 chiều** (A→B và B→A) để truy vấn đơn giản.
- Không có thuộc tính; nếu cần mở rộng có thể thêm `since` (ngày kết bạn).

### 3.3 Constraint nên tạo (chạy trong Neo4j Browser)

```cypher
CREATE CONSTRAINT user_id_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.id IS UNIQUE;
```

### 3.4 Các truy vấn chính hệ thống dùng

```cypher
// Danh sách bạn bè
MATCH (:User {id:$id})-[:FRIEND]->(f:User) RETURN f.id;

// Gợi ý kết bạn (friend-of-friend, xếp theo số bạn chung)
MATCH (me:User {id:$id})-[:FRIEND]->()-[:FRIEND]->(fof:User)
WHERE fof.id <> $id AND NOT (me)-[:FRIEND]->(fof)
RETURN fof.id, count(*) AS mutual ORDER BY mutual DESC LIMIT 10;

// Bạn chung giữa 2 người
MATCH (:User {id:$a})-[:FRIEND]->(m:User)<-[:FRIEND]-(:User {id:$b})
RETURN m.id, m.username;
```

### 3.5 Nguyên tắc phân chia dữ liệu giữa 2 mô hình

| Dữ liệu | MongoDB | Neo4j |
|---|---|---|
| Hồ sơ người dùng | Lưu đầy đủ (nguồn sự thật) | Chỉ `id`, `username`, `full_name` |
| Bài viết / bình luận / hình ảnh | Lưu đầy đủ | Không lưu |
| Quan hệ bạn bè | Chỉ cache `friend_count` | **Nguồn sự thật** (`FRIEND`) |
| Gợi ý kết bạn | Có thể cache kết quả | Tính trực tiếp từ đồ thị |

---

## 4. Phân quyền (Authorization)

Hệ thống có **2 tầng** phân quyền:

### 4.1 Tầng ứng dụng (đã cài trong code)

| Role | Quyền |
|---|---|
| `user` | Đăng nhập, đăng bài, bình luận, thích, kết bạn, xem feed/gợi ý/cộng đồng, xem hồ sơ |
| `admin` | Tất cả quyền `user` + nhóm API `/admin/*` (health, shard-distribution, benchmark, outbox) + trang "Giám sát" trên web |

**Cơ chế hoạt động:**
1. Đăng nhập `POST /users/login` → trả về document user có trường `role`.
2. PHP lưu user vào `$_SESSION`, mọi request sang Python API tự gắn header `X-User-Id` (xem `mini_social_php/app/api_client.php`).
3. FastAPI dependency `require_admin` (trong `backend-python/app/routers/admin.py`) đọc header, tra `users.role` trong MongoDB:
   - Thiếu header → **401**; user không tồn tại → **401**; role ≠ admin → **403**.
4. Trang web: menu "⚙️ Giám sát" chỉ hiện với admin; truy cập thẳng URL cũng bị chặn trong `index.php`.

**Tài khoản mặc định sau khi seed:** `admin` / `admin123` (role admin), `user000`–`user029` / `123456` (role user).

### 4.2 Tầng CSDL (tùy chọn — khuyến nghị khi demo bảo mật)

**MongoDB** — script [scripts/create_db_users.js](../scripts/create_db_users.js) tạo 3 tài khoản theo nguyên tắc least-privilege:

| Tài khoản | Role MongoDB | Dùng cho |
|---|---|---|
| `cluster_admin` | `root` | Quản trị cluster (thành viên phụ trách hạ tầng) |
| `backend_app` | `readWrite` trên `social` | Backend Python kết nối |
| `report_viewer` | `read` trên `social` + `clusterMonitor` | Thành viên xem dữ liệu, giám sát |

Bật authentication cho sharded cluster (làm trên **cả 4 máy**):
```powershell
# 1. Tạo keyFile chung trên PC4 rồi copy sang PC1-PC3 (cùng nội dung):
openssl rand -base64 756 > C:\data\mongo-keyfile
# 2. Thêm vào MỌI file .cfg (configsvr.cfg, shard*.cfg):
#    security:
#      keyFile: C:\data\mongo-keyfile
#    và thêm --keyFile C:\data\mongo-keyfile vào lệnh mongos
# 3. Khởi động lại cluster, tạo user qua mongos:
mongosh --host <PC4_IP> --port 27017 scripts/create_db_users.js
# 4. Sửa .env:
#    MONGO_URI=mongodb://backend_app:BackendApp%402026@<PC4_IP>:27017/?authSource=admin&retryWrites=true&w=majority
```

**Neo4j** — script [scripts/create_neo4j_users.cypher](../scripts/create_neo4j_users.cypher): tạo `backend_app` (role `editor`) và `report_viewer` (role `reader`), sau đó sửa `NEO4J_USER`/`NEO4J_PASSWORD` trong `.env`.

---

## 5. Triển khai từng bước (tóm tắt)

```powershell
# B1. Mỗi máy: copy .env.example → .env, điền IP 4 máy, mở firewall LAN
# B2. PC1: .\deploy\pc1-configsvr\start_configsvr.ps1
#     PC2: .\deploy\pc2-shard1\start_shard1.ps1
#     PC3: .\deploy\pc3-shard2\start_shard2.ps1
# B3. PC4: powershell -File scripts\init_cluster.ps1   (mở mongos song song bằng start_mongos.ps1)
# B4. PC4: cài Neo4j Desktop theo deploy\pc4-master\NEO4J_SETUP.md
# B5. PC4: cd backend-python; pip install -r requirements.txt
#          .\..\deploy\pc4-master\start_backend.ps1
# B6. PC4: python scripts\seed_data.py 30 20
# B7. Kiểm thử: python benchmark\benchmark.py  +  Postman (mục 7)
```

---

## 6. Danh sách API

| Method | Endpoint | Quyền | Mô tả |
|---|---|---|---|
| POST | `/users` | công khai | Đăng ký (dual-write Mongo+Neo4j; `?strong=true` = rollback nếu Neo4j chết) |
| POST | `/users/login` | công khai | Đăng nhập, trả user + `role` |
| GET | `/users`, `/users/{id}` | đã đăng nhập* | Danh sách / chi tiết user (không trả `password_hash`) |
| POST | `/posts` | user | Đăng bài → shard theo `hash(author_id)` |
| GET | `/posts/by-author/{id}` | user | **Targeted query** (1 shard) |
| GET | `/posts/search?q=` | user | **Scatter-gather** (mọi shard) |
| POST | `/posts/{id}/like` | user | Tăng like atomic |
| POST | `/posts/comments` | user | Bình luận |
| GET | `/posts/{id}/comments` | user | Danh sách bình luận |
| POST | `/social/friends` | user | Kết bạn (Neo4j + cache Mongo) |
| GET | `/social/friends/{id}` | user | Danh sách bạn (Neo4j) |
| GET | `/social/feed/{id}` | user | **Liên mô hình**: Neo4j → MongoDB |
| GET | `/social/suggestions/{id}` | user | Friend-of-friend + hồ sơ Mongo |
| GET | `/social/communities` | user | Phát hiện cộng đồng |
| GET | `/admin/health` | **admin** | Trạng thái Mongo/Neo4j/shards/outbox |
| GET | `/admin/shard-distribution` | **admin** | Số docs mỗi shard |
| GET | `/admin/benchmark?runs=` | **admin** | Đo targeted vs scatter-gather vs secondary |
| POST | `/admin/outbox/process` | **admin** | Retry đồng bộ Neo4j thủ công |

\* Giao diện web ép đăng nhập; gọi API trực tiếp các endpoint đọc là công khai (demo học thuật).

---

## 7. Test API bằng Postman

1. Mở Postman → **Import** → chọn file [postman/MiniSocial.postman_collection.json](../postman/MiniSocial.postman_collection.json).
2. Trong collection, sửa biến `base_url` → `http://<PC4_IP>:8000`.
3. Chạy theo thứ tự thư mục **1 → 5**:
   - **1. Auth**: chạy "Đăng nhập (admin)", "Đăng nhập (user000)", "Đăng nhập (user001)" — các biến `admin_id`, `user_id`, `user2_id` **tự lưu** nhờ test script.
   - **3. Posts**: "Tạo bài viết" tự lưu `post_id` cho các request sau.
   - **5. Admin**: tự gắn `X-User-Id: {{admin_id}}`; có sẵn 2 request kiểm tra phân quyền (mong đợi **401** khi thiếu header, **403** khi dùng user thường).
4. Hoặc chạy cả collection: **Runner** → chọn collection → Run (các assertion pass/fail hiển thị từng request — chụp màn hình làm minh chứng báo cáo).

### Kịch bản test chịu lỗi bằng Postman
| Bước | Thao tác | Kết quả mong đợi |
|---|---|---|
| 1 | Stop Neo4j Desktop trên PC4 | — |
| 2 | Chạy "Đăng ký user mới" | 200, `sync: "pending_outbox"` |
| 3 | Chạy "Đăng ký - strong=true" | **503** (đã rollback Mongo) |
| 4 | Chạy "News Feed" | 200, `degraded: true` |
| 5 | Start lại Neo4j, đợi ≤10s, chạy "Trạng thái các nút" | `outbox_pending: 0` |
| 6 | Tắt mongod trên PC2, chạy "Bài viết theo tác giả" | Vẫn 200 (đọc secondary trên PC3) |
