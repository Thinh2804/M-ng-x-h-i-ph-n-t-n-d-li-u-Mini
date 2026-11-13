<?php
require_once __DIR__ . '/../app/bootstrap.php';
requireLogin();
$me = currentUserId();
$action = $_POST['action'] ?? '';
switch ($action) {
    case 'create_post':
        $result = api('POST', apiPath('posts'), ['author_id' => $me, 'content' => trim($_POST['content'] ?? ''), 'image_urls' => []]);
        $ok = 'Đã đăng bài.';
        break;
    case 'like':
        $result = api('POST', apiPath('like', ['post_id' => $_POST['post_id'] ?? '']));
        $ok = 'Đã thích bài viết.';
        break;
    case 'comment':
        $result = api('POST', apiPath('comments'), ['post_id' => $_POST['post_id'] ?? '', 'author_id' => $me, 'content' => trim($_POST['content'] ?? '')]);
        $ok = 'Đã gửi bình luận.';
        break;
    case 'add_friend':
        $result = api('POST', apiPath('friend_add'), ['from_user' => $me, 'to_user' => $_POST['user_id'] ?? '']);
        $ok = 'Đã kết bạn.';
        break;
    case 'process_outbox':
        requireAdmin();
        $result = api('POST', apiPath('outbox_process'));
        $ok = 'Đã xử lý ' . (int)($result['data']['processed'] ?? 0) . ' sự kiện outbox.';
        break;
    default:
        flash('error', 'Thao tác không hợp lệ.');
        header('Location: feed.php');
        exit;
}
if ($result['ok']) flash('success', $ok);
else flash('error', apiMessage($result, 'Không thể thực hiện thao tác.'));
// Chỉ quay lại các trang nội bộ đã biết, giữ query string (vd. profile.php?user_id=...)
$back = $_SERVER['HTTP_REFERER'] ?? 'feed.php';
$target = basename(parse_url($back, PHP_URL_PATH) ?: 'feed.php');
$query = parse_url($back, PHP_URL_QUERY);
$allowed = ['feed.php', 'friends.php', 'profile.php', 'admin.php', 'post.php'];
header('Location: ' . (in_array($target, $allowed, true) ? $target . ($query ? '?' . $query : '') : 'feed.php'));
exit;
