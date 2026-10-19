# PC4 - Hướng dẫn cài Neo4j Desktop

Theo quy trình, PC4 chạy **Neo4j Desktop** (không dùng Docker):

1. Tải Neo4j Desktop: https://neo4j.com/download/
2. Tạo Project mới → **Add → Local DBMS**:
   - Name: `social-graph`
   - Password: giá trị `NEO4J_PASSWORD` trong file `.env` (mặc định `social_graph_2026`)
   - Version: 5.x
3. Trước khi Start, vào **Settings** của DBMS và sửa để máy khác truy cập được:
   ```
   server.default_listen_address=0.0.0.0
   server.bolt.listen_address=0.0.0.0:7687
   ```
4. **Start** DBMS. Kiểm tra từ máy khác:
   ```
   # Neo4j Browser: http://<PC4_IP>:7474
   # Bolt:          bolt://<PC4_IP>:7687
   ```
5. Mở firewall cổng `7474` và `7687` trong mạng LAN (không mở ra Internet).

> Backend Python kết nối qua `NEO4J_URI=bolt://<PC4_IP>:7687` trong `.env`.
