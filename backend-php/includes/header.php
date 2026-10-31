<?php /* Layout chung - $me là user đang đăng nhập (hoặc null) */ ?>
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mạng Xã Hội Mini - MongoDB + Neo4j</title>
<style>
  * { box-sizing: border-box; margin: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; color: #1c1e21; }
  nav { background: #1877f2; color: #fff; padding: 12px 24px; display: flex; gap: 20px; align-items: center; flex-wrap: wrap; }
  nav a { color: #fff; text-decoration: none; font-weight: 600; }
  nav a:hover { text-decoration: underline; }
  nav .spacer { flex: 1; }
  .container { max-width: 860px; margin: 24px auto; padding: 0 16px; }
  .card { background: #fff; border-radius: 10px; padding: 18px; margin-bottom: 16px;
          box-shadow: 0 1px 3px rgba(0,0,0,.12); }
  .card h3 { margin-bottom: 6px; }
  .meta { color: #65676b; font-size: 13px; margin-bottom: 8px; }
  input, textarea, select { width: 100%; padding: 9px; margin: 5px 0 10px;
          border: 1px solid #ccd0d5; border-radius: 6px; font-size: 14px; }
  button { background: #1877f2; color: #fff; border: 0; padding: 9px 18px;
          border-radius: 6px; font-weight: 600; cursor: pointer; }
  button:hover { background: #166fe5; }
  .badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
  .ok   { background: #d4f8d4; color: #1a7f37; }
  .down { background: #ffd6d6; color: #c0392b; }
  .warn { background: #fff3cd; color: #856404; }
  table { width: 100%; border-collapse: collapse; }
  th, td { padding: 8px 10px; border-bottom: 1px solid #eee; text-align: left; font-size: 14px; }
  .alert { padding: 10px 14px; border-radius: 6px; margin-bottom: 14px; }
</style>
</head>
<body>
<nav>
  <strong>🌐 MiniSocial</strong>
  <?php if ($me): ?>
    <a href="index.php">Bảng tin</a>
    <a href="index.php?page=users">Người dùng</a>
    <a href="index.php?page=suggestions">Gợi ý kết bạn</a>
    <a href="index.php?page=communities">Cộng đồng</a>
    <a href="index.php?page=profile">Hồ sơ</a>
    <?php if (($me['role'] ?? '') === 'admin'): ?>
      <a href="index.php?page=admin">⚙️ Giám sát</a>
      <a href="index.php?page=sync">🔄 Đồng bộ</a>
    <?php endif; ?>
    <span class="spacer"></span>
    <span>👤 <?= e($me['username']) ?><?= ($me['role'] ?? '') === 'admin' ? ' (admin)' : '' ?></span>
    <a href="index.php?action=logout">Đăng xuất</a>
  <?php else: ?>
    <span class="spacer"></span>
    <a href="index.php?page=login">Đăng nhập</a>
  <?php endif; ?>
</nav>
<div class="container">
