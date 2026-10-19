<?php /* Đăng nhập / Đăng ký */ ?>
<div class="card" style="max-width:420px;margin:40px auto">
  <h3>🔐 Đăng nhập</h3>
  <form method="post">
    <input type="hidden" name="action" value="login">
    <input name="username" placeholder="Username" required>
    <input type="password" name="password" placeholder="Mật khẩu" required>
    <button style="width:100%">Đăng nhập</button>
  </form>
  <p class="meta" style="margin-top:8px">
    Dữ liệu mẫu: user000 … user029, mật khẩu <code>123456</code><br>
    Tài khoản quản trị: <code>admin</code> / <code>admin123</code>
  </p>
</div>

<div class="card" style="max-width:420px;margin:0 auto">
  <h3>📝 Đăng ký (dual-write MongoDB + Neo4j)</h3>
  <form method="post">
    <input type="hidden" name="action" value="register">
    <input name="username" placeholder="Username" required>
    <input type="password" name="password" placeholder="Mật khẩu (≥ 4 ký tự)" required>
    <input name="full_name" placeholder="Họ tên">
    <button style="width:100%">Đăng ký</button>
  </form>
</div>
