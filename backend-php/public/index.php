<?php
session_start();
require __DIR__ . '/../includes/api.php';

$me   = $_SESSION['user'] ?? null;
$page = $_GET['page'] ?? 'feed';
$msg  = null;

// ---- Đăng xuất ----
if (($_GET['action'] ?? '') === 'logout') {
    session_destroy();
    header('Location: index.php?page=login');
    exit;
}

// ---- Xử lý POST ----
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    switch ($_POST['action'] ?? '') {
        case 'login':
            [$r, $c] = api('POST', '/users/login', [
                'username' => $_POST['username'],
                'password' => $_POST['password'],
            ]);
            if ($c === 200) {
                $_SESSION['user'] = $r;
                header('Location: index.php');
                exit;
            }
            $msg = '❌ ' . ($r['detail'] ?? 'Đăng nhập thất bại');
            break;
        case 'register':
            [$r, $c] = api('POST', '/users', [
                'username'  => $_POST['username'],
                'password'  => $_POST['password'],
                'full_name' => $_POST['full_name'] ?? '',
            ]);
            $msg = $c === 200
                ? "✅ Đăng ký thành công (sync: {$r['sync']}) - hãy đăng nhập"
                : '❌ ' . ($r['detail'] ?? 'Lỗi');
            break;
        case 'create_post':
            if (!$me) break;
            [$r, $c] = api('POST', '/posts', [
                'author_id' => $me['_id'],
                'content'   => $_POST['content'],
                'image_urls'=> array_filter([trim($_POST['image_url'] ?? '')]),
            ]);
            $msg = $c === 200 ? '✅ Đã đăng bài (ghi vào shard qua mongos)' : '❌ ' . ($r['detail'] ?? 'Lỗi');
            break;
        case 'add_friend':
            if (!$me) break;
            [$r, $c] = api('POST', '/social/friends', [
                'from_user' => $me['_id'],
                'to_user'   => $_POST['to_user'],
            ]);
            $msg = $c === 200 ? '✅ Đã kết bạn (ghi Neo4j trên PC4)' : '❌ ' . ($r['detail'] ?? 'Lỗi');
            break;
        case 'comment':
            if (!$me) break;
            [$r, $c] = api('POST', '/posts/comments', [
                'post_id'   => $_POST['post_id'],
                'author_id' => $me['_id'],
                'content'   => $_POST['content'],
            ]);
            $msg = $c === 200 ? '✅ Đã bình luận' : '❌ ' . ($r['detail'] ?? 'Lỗi');
            break;
        case 'like':
            api('POST', '/posts/' . urlencode($_POST['post_id']) . '/like');
            $msg = '👍 Đã thích';
            break;
    }
}

// Chưa đăng nhập → chỉ cho xem trang login
if (!$me && $page !== 'login') {
    $page = 'login';
}
// Trang giám sát chỉ dành cho admin
if ($page === 'admin' && (($me['role'] ?? '') !== 'admin')) {
    $page = 'feed';
    $msg  = $msg ?? '❌ Chỉ tài khoản admin được xem trang giám sát cluster';
}

[$users, ] = api('GET', '/users?limit=100');

require __DIR__ . '/../includes/header.php';

if ($msg) {
    echo '<div class="alert card">' . e($msg) . '</div>';
}

switch ($page) {
    case 'login':        require __DIR__ . '/../pages/login.php'; break;
    case 'users':        require __DIR__ . '/../pages/users.php'; break;
    case 'suggestions':  require __DIR__ . '/../pages/suggestions.php'; break;
    case 'communities':  require __DIR__ . '/../pages/communities.php'; break;
    case 'profile':      require __DIR__ . '/../pages/profile.php'; break;
    case 'admin':        require __DIR__ . '/../pages/admin.php'; break;
    default:             require __DIR__ . '/../pages/feed.php'; break;
}
?>
</div>
</body>
</html>
