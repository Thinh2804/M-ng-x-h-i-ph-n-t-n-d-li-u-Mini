# UniConnect – PHP Frontend (mini_social_php)

Giao diện PHP responsive cho Mini Social Network theo phạm vi Frontend Developer trong SRS: đăng nhập/đăng ký, News Feed, Profile, Friends/FoF và Admin Dashboard.

## 1. Công nghệ và kiến trúc
- PHP 8.1+ (khuyến nghị PHP 8.2+), HTML5, CSS3, JavaScript thuần.
- PHP gọi Python FastAPI qua HTTP/cURL. PHP không kết nối trực tiếp MongoDB hoặc Neo4j.
- Mặc định FastAPI: `http://127.0.0.1:8000`; PHP web server: `http://127.0.0.1:8080`.
- Header `X-User-Id` được gửi khi đã đăng nhập. Nếu Backend trả access token, PHP cũng gửi Bearer token.

## 2. Cấu trúc
```
mini_social_php/
├── config.php
├── README.md
├── app/
│   ├── api_client.php
│   ├── bootstrap.php
│   └── layout.php
└── public/
    ├── index.php
    ├── login.php
    ├── register.php
    ├── logout.php
    ├── feed.php
    ├── profile.php
    ├── friends.php
    ├── admin.php
    ├── action.php
    └── assets/{css/style.css,js/app.js}
```

## 3. Chạy trên Windows 11
1. Trên máy chạy cụm giả lập: `deploy\start_local.ps1` đã tự chạy frontend này ở cổng 8080. Chạy tay thì làm tiếp các bước dưới tại thư mục `mini_social_php`.
2. Bật extension cURL và mbstring trong `php.ini` (`extension=curl`, `extension=mbstring`).
3. Mở PowerShell tại thư mục dự án:
   ```powershell
   php -S 0.0.0.0:8080 -t public
   ```
4. Mở `http://127.0.0.1:8080`.
5. Đảm bảo FastAPI đang chạy trên PC4 cổng 8000. Nếu PHP và FastAPI khác máy, sửa `base_url` trong `config.php` (hoặc đặt biến môi trường `API_BASE_URL`) thành IP LAN của PC chạy FastAPI.

## 4. API contract (khớp backend-python/app/routers)
Mọi route gom tại `config.php`. `{user_id}` mặc định là user đang đăng nhập; mọi request gửi kèm `X-User-Id`.

| Key | Method | Path | Dùng ở |
|---|---|---|---|
| register | POST | `/users` `{username, password, full_name}` | register.php |
| login | POST | `/users/login` → user (`_id`, `role`…) | login.php |
| users | GET | `/users?limit=1000` | tra tên bạn bè, người bình luận |
| profile | GET | `/users/{user_id}` | profile.php |
| user_posts | GET | `/posts/by-author/{user_id}` (targeted, 1 shard) | profile.php |
| feed | GET | `/social/feed/{user_id}` → `{degraded, friend_count, posts}` | feed.php |
| search | GET | `/posts/search?q=` (scatter-gather) | ô tìm kiếm → feed.php?q= |
| posts | POST | `/posts` `{author_id, content, image_urls}` | action.php |
| like | POST | `/posts/{post_id}/like` | action.php |
| post | GET | `/posts/{post_id}` | post.php |
| post_view | POST | `/posts/{post_id}/view` (ghi nhận đã xem → sở thích) | post.php |
| post_comments | GET | `/posts/{post_id}/comments` | feed.php |
| comments | POST | `/posts/comments` `{post_id, author_id, content}` | action.php |
| friends | GET | `/social/friends/{user_id}` → `{friends: [id…]}` | friends.php, profile.php |
| friend_add | POST | `/social/friends` `{from_user, to_user}` | action.php |
| suggestions | GET | `/social/suggestions/{user_id}` → `{suggestions}` | friends.php |
| health | GET | `/admin/health` (chỉ admin) | admin.php |
| shards | GET | `/admin/shard-distribution` (chỉ admin) | admin.php |
| outbox_process | POST | `/admin/outbox/process` (chỉ admin) | admin.php |

**Gợi ý kết bạn theo nội dung:** đăng / mở xem (post.php) / thích / bình luận một bài sẽ ghi từ khóa của bài thành `(:User)-[:INTERESTED_IN]->(:Keyword)` trên Neo4j, và nối `(:User)-[:CONTENT_MATCH]-(:User)` với tác giả bài đó (hoặc 5 người khớp nhất khi tự đăng bài). Vì vậy user mới chưa có bạn vẫn có gợi ý, và người bị khớp cũng thấy user mới ở đầu danh sách gợi ý của họ. Dữ liệu cũ: chạy `python scripts/backfill_interests.py` một lần.

Khi feed/gợi ý trả `degraded: true` (Neo4j không khả dụng), giao diện hiện cảnh báo và chỉ hiển thị dữ liệu MongoDB còn lấy được.

## 5. Quy ước dữ liệu
Frontend giữ nguyên tên trường SRS như `user_id`, `author_id`, `post_id`, `friend_count`, `image_urls`, `created_at`, `outbox`. Phần mapping response linh hoạt ở mức đọc các alias phổ biến, không đổi schema lưu trữ Backend.

## 6. Mã lỗi
- 401: phiên đăng nhập không hợp lệ/hết hạn.
- 403: không đủ quyền.
- 503 hoặc không kết nối được: Backend chưa sẵn sàng.

## 7. Giới hạn hiện tại
- Form đăng bài hiện gửi nội dung văn bản và `image_urls: []`; upload ảnh cần Backend cung cấp endpoint upload hoặc quy định URL ảnh.
- Chia sẻ, thông báo và phân trang chưa có API được mô tả đầy đủ trong SRS nên chưa giả lập hành vi ghi dữ liệu.
- Dashboard chỉ hiển thị trạng thái Backend trả về; không tự tạo số liệu giả khi Cluster/Outbox chưa phản hồi.
