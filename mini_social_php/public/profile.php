<?php
require_once __DIR__ . '/../app/bootstrap.php';
require_once __DIR__ . '/../app/layout.php';
requireLogin();

$uid = (string)($_GET['user_id'] ?? currentUserId());
$isMe = $uid === currentUserId();
$r = api('GET', apiPath('profile', ['user_id' => $uid]));
$p = $r['ok'] && is_array($r['data']) ? $r['data'] : ($isMe ? currentUser() : []);
// Bài viết theo author_id = shard key → truy vấn targeted, chỉ chạm 1 shard
$pr = api('GET', apiPath('user_posts', ['user_id' => $uid]));
$posts = $pr['ok'] && is_array($pr['data']) ? $pr['data'] : [];
$name = ($p['full_name'] ?? '') ?: ($p['username'] ?? 'Thành viên');
$isFriend = !$isMe && in_array($uid, (array)(api('GET', apiPath('friends'))['data']['friends'] ?? []), true);

renderHeader('Trang cá nhân', 'profile');
?>
<div class="page-heading"><div><div class="eyebrow">HỒ SƠ THÀNH VIÊN</div><h1><?= $isMe ? 'Trang cá nhân' : e($name) ?></h1><p class="muted">Thông tin và những chia sẻ của thành viên.</p></div></div>
<?php if (!$r['ok']): ?>
  <div class="backend-notice"><span class="notice-icon">!</span><div><strong>Chưa tải được hồ sơ từ Backend</strong><p><?= e(apiMessage($r, 'Không thể tải hồ sơ.')) ?></p></div></div>
<?php endif; ?>
<section class="profile-cover card">
  <div class="cover-decoration"></div>
  <div class="profile-main">
    <span class="avatar avatar-xl"><?= e(initial($name)) ?></span>
    <div class="profile-identity"><h2><?= e($name) ?></h2><p>@<?= e($p['username'] ?? 'member') ?><?= ($p['role'] ?? '') === 'admin' ? ' · quản trị viên' : '' ?></p></div>
    <div class="profile-stats">
      <div><strong><?= count($posts) ?></strong><span>Bài viết</span></div>
      <div><strong><?= e($p['friend_count'] ?? 0) ?></strong><span>Bạn bè</span></div>
      <?php if (!$isMe && !$isFriend && $r['ok']): ?>
        <form method="post" action="action.php"><input type="hidden" name="user_id" value="<?= e($uid) ?>"><button class="btn btn-primary" name="action" value="add_friend">＋ Kết bạn</button></form>
      <?php elseif ($isFriend): ?>
        <span class="status-label good">✓ Bạn bè</span>
      <?php endif; ?>
    </div>
  </div>
</section>
<div class="section-heading"><div><h2>Bài viết</h2><p class="muted">Những nội dung đã chia sẻ</p></div></div>
<div class="feed-column profile-posts">
  <?php foreach ($posts as $post): ?>
  <article class="post-card card">
    <div class="post-head"><span class="avatar"><?= e(initial($name)) ?></span><div class="post-author"><strong><?= e($name) ?></strong><small><?= e(fmtTime($post['created_at'] ?? null)) ?></small></div></div>
    <div class="post-content"><?= nl2br(e($post['content'] ?? '')) ?></div>
    <div class="post-stats"><span>♡ <?= e($post['likes'] ?? 0) ?> lượt thích</span></div>
  </article>
  <?php endforeach; ?>
  <?php if (!$posts): ?>
    <div class="empty-state card"><div class="empty-art">◎</div><h3>Chưa có bài viết</h3><p>Các bài viết của thành viên sẽ hiển thị tại đây.</p><a class="btn btn-soft" href="feed.php">Trở về bảng tin</a></div>
  <?php endif; ?>
</div>
<?php renderFooter(); ?>
