# MiniSocial – PHP Web Frontend & Admin

Frontend PHP theo phân công Frontend Developer, tích hợp Python FastAPI và bám SRS Mạng xã hội Mini (MongoDB Sharded Cluster + Neo4j).

## 1. Cấu trúc

- `public/login.php`, `register.php`: đăng nhập/đăng ký.
- `public/feed.php`: News Feed, đăng bài, Like, bình luận.
- `public/profile.php`: hồ sơ và bài viết cá nhân.
- `public/friends.php`: bạn bè và gợi ý FoF.
- `public/admin.php`: Health Check, trạng thái MongoDB/Neo4j, Shard, Outbox.
- `app/bootstrap.php`: session, kiểm tra quyền, hàm gọi API tập trung.
- `config.php`: cấu hình URL FastAPI.

## 2. Chạy thử trên PC4 (Windows)

1. Cài PHP 8+ và bật extension `curl` trong `php.ini`.
2. Giải nén thư mục dự án, mở terminal tại thư mục `mini_social_php`.
3. Chạy: `php -S 0.0.0.0:8080 -t public`
4. Mở `http://localhost:8080` hoặc `http://IP_PC4:8080` từ máy trong LAN.
5. Sửa `API_BASE_URL` trong `config.php` thành địa chỉ FastAPI thực tế, ví dụ `http://192.168.1.104:8000`.

Nếu PHP và FastAPI chạy cùng PC4, `127.0.0.1:8000` là phù hợp. Trình duyệt người dùng không gọi trực tiếp FastAPI; PHP gọi backend bằng cURL nên tránh vấn đề CORS ở phía trình duyệt.

## 3. API contract frontend đang sử dụng

SRS mô tả chức năng và cổng FastAPI `8000`, nhưng chưa quy định URL endpoint và JSON response cụ thể. Frontend tạm thống nhất quy ước REST dưới đây; cần đối chiếu/đồng bộ với backend trước khi nghiệm thu:

| Method | Endpoint | Payload / mục đích |
|---|---|---|
| POST | `/api/v1/auth/register` | `username`, `password`, `full_name` |
| POST | `/api/v1/auth/login` | `username`, `password`; response có `user` |
| GET | `/api/v1/feed` | response `posts` |
| POST | `/api/v1/posts` | `content`, `image_urls` |
| POST | `/api/v1/posts/{post_id}/like` | tăng likes |
| POST | `/api/v1/posts/{post_id}/comments` | `content` |
| GET | `/api/v1/users/{user_id}` | `user`, `posts` |
| GET | `/api/v1/friends` | `friends` |
| GET | `/api/v1/friends/suggestions` | `suggestions`, số `mutual_friends` |
| POST | `/api/v1/friends` | `target_user_id` |
| GET | `/api/v1/admin/health` | sức khỏe hệ thống |
| GET | `/api/v1/admin/shards` | `shards` |
| GET | `/api/v1/admin/outbox` | `pending`, `done`, `failed` |

Tất cả request sau đăng nhập gửi header `X-User-Id` đúng theo SRS. Các API admin chỉ được gọi khi session có `role=admin`; backend vẫn phải tự xác minh role và trả 401/403, không được tin vào kiểm tra giao diện PHP.

## 4. Quy tắc tên

- PHP file: `snake_case.php`; PHP variables: `$snake_case`; PHP functions: `camelCase()`.
- JavaScript variables/functions: `camelCase`.
- CSS class: `kebab-case`.
- MongoDB field/collection: giữ đúng SRS (`author_id`, `friend_count`, `image_urls`, `created_at`, `users`, `posts`, `comments`, `outbox`).
- Graph model: `User`, `FRIEND`.

## 5. Điểm cần hoàn thiện trước triển khai thật

- SRS dùng `X-User-Id`; đây là cơ chế nhận diện theo tài liệu nhưng không đủ an toàn nếu client có thể tự giả mạo header. Nên bổ sung access token/session ký số hoặc xác thực cookie phía backend; FastAPI phải kiểm tra quyền ở mọi endpoint.
- Nên dùng HTTPS, CSRF token cho form, giới hạn tần suất đăng nhập/đăng bài và kiểm tra URL ảnh ở backend.
- Đảm bảo response API thống nhất với contract ở mục 3; nếu backend đang dùng đường dẫn khác, chỉ cần sửa endpoint trong các file PHP tương ứng hoặc tạo lớp mapping tập trung.
- Các thông tin trạng thái Shard/Outbox phụ thuộc dữ liệu backend trả về; dashboard có fallback “Chưa rõ/—” khi trường chưa có.
