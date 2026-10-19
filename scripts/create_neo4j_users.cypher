// Tạo tài khoản phân quyền Neo4j - chạy trong Neo4j Browser (http://<PC4_IP>:7474)
// đăng nhập bằng tài khoản neo4j, chạy từng lệnh trên database "system".

// 1. Tài khoản backend - đọc/ghi đồ thị social
CREATE USER backend_app IF NOT EXISTS SET PASSWORD 'BackendApp@2026' CHANGE NOT REQUIRED;
GRANT ROLE editor TO backend_app;

// 2. Tài khoản xem báo cáo - chỉ đọc
CREATE USER report_viewer IF NOT EXISTS SET PASSWORD 'Viewer@2026' CHANGE NOT REQUIRED;
GRANT ROLE reader TO report_viewer;

// Kiểm tra: SHOW USERS;
// Sau đó sửa .env: NEO4J_USER=backend_app, NEO4J_PASSWORD=BackendApp@2026
