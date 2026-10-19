// Tạo tài khoản phân quyền MỨC CSDL MongoDB - chạy qua mongos trên PC4:
//   mongosh --host <PC4_IP> --port 27017 scripts/create_db_users.js
// LƯU Ý: chỉ có hiệu lực khi bật authentication (xem docs/HUONG_DAN_TOAN_PHAN.md mục 6.3:
// cần keyFile chung cho mọi mongod/mongos trong cluster).

// 1. Quản trị cluster - toàn quyền
db.getSiblingDB("admin").createUser({
  user: "cluster_admin",
  pwd: "ClusterAdmin@2026",
  roles: [
    { role: "root", db: "admin" }
  ]
});

// 2. Backend Python - chỉ đọc/ghi DB social (least privilege)
db.getSiblingDB("admin").createUser({
  user: "backend_app",
  pwd: "BackendApp@2026",
  roles: [
    { role: "readWrite", db: "social" }
  ]
});

// 3. Thành viên nhóm xem dữ liệu/giám sát - chỉ đọc
db.getSiblingDB("admin").createUser({
  user: "report_viewer",
  pwd: "Viewer@2026",
  roles: [
    { role: "read", db: "social" },
    { role: "clusterMonitor", db: "admin" }
  ]
});

print("Đã tạo 3 tài khoản: cluster_admin (root), backend_app (readWrite social), report_viewer (read + clusterMonitor)");
print("Sau khi bật auth, sửa MONGO_URI trong .env:");
print("  mongodb://backend_app:BackendApp%402026@<PC4_IP>:27017/?authSource=admin&retryWrites=true&w=majority");
