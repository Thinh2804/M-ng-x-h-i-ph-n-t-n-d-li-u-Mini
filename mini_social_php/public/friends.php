<?php
require_once __DIR__ . '/../app/bootstrap.php';
require_once __DIR__ . '/../app/layout.php';
requireLogin();

$fr = api('GET', apiPath('friends'));
$sg = api('GET', apiPath('suggestions'));
$dir = userDirectory();
// API bạn bè (Neo4j) chỉ trả về danh sách user_id → tra hồ sơ từ MongoDB
$friendIds = $fr['ok'] ? ($fr['data']['friends'] ?? []) : [];
$friends = [];
foreach (is_array($friendIds) ? $friendIds : [] as $id) {
    $friends[] = ['user_id' => $id] + ($dir[$id] ?? []);
}
$suggestions = $sg['ok'] ? ($sg['data']['suggestions'] ?? []) : [];
if (!is_array($suggestions)) $suggestions = [];
$sgDegraded = !empty($sg['data']['degraded']);

renderHeader('Bạn bè', 'friends');
?>
<div class="page-heading"><div><div class="eyebrow">MỞ RỘNG KẾT NỐI</div><h1>Bạn bè <span class="heading-spark">✦</span></h1><p class="muted">Giữ liên lạc và khám phá những kết nối mới.</p></div></div>

<div class="section-heading"><div><h2>Gợi ý kết bạn</h2><p class="muted">Bạn của bạn bè và người cùng chủ đề quan tâm (Neo4j)</p></div><span class="count-pill"><?= count($suggestions) ?> gợi ý</span></div>
<?php if (!$sg['ok'] || $sgDegraded): ?>
  <div class="backend-notice"><span class="notice-icon">!</span><div><strong>Chưa tải được gợi ý kết bạn</strong><p><?= e($sgDegraded ? ($sg['data']['reason'] ?? 'Neo4j không khả dụng') : apiMessage($sg, 'Kiểm tra kết nối Neo4j thông qua Backend.')) ?></p></div></div>
<?php endif; ?>
<div class="people-grid">
  <?php foreach ($suggestions as $person): $n = $person['full_name'] ?: ($person['username'] ?? 'Thành viên'); ?>
  <article class="person-card card">
    <div class="person-banner"><span class="person-avatar"><?= e(initial($n)) ?></span></div>
    <div class="person-info">
      <a href="profile.php?user_id=<?= e($person['user_id'] ?? '') ?>"><strong><?= e($n) ?></strong></a>
      <small>@<?= e($person['username'] ?? 'member') ?></small>
      <span class="mutual">♧ <?= e(suggestionReason($person)) ?> · <?= e($person['post_count'] ?? 0) ?> bài viết</span>
      <form method="post" action="action.php"><input type="hidden" name="user_id" value="<?= e($person['user_id'] ?? '') ?>"><button class="btn btn-primary btn-full" name="action" value="add_friend">＋ Kết bạn</button></form>
    </div>
  </article>
  <?php endforeach; ?>
  <?php if (!$suggestions): ?>
    <div class="empty-state card grid-empty"><div class="empty-art">♧</div><h3>Chưa có gợi ý mới</h3><p>Hãy đăng bài hoặc mở xem bài viết bạn thích, hệ thống sẽ gợi ý những người cùng chủ đề.</p></div>
  <?php endif; ?>
</div>

<div class="section-heading friends-heading"><div><h2>Danh sách bạn bè</h2><p class="muted">Những kết nối hiện tại của bạn</p></div><span class="count-pill"><?= count($friends) ?> bạn bè</span></div>
<?php if (!$fr['ok']): ?>
  <div class="backend-notice"><span class="notice-icon">!</span><div><strong>Chưa tải được danh sách bạn bè</strong><p><?= e(apiMessage($fr, 'Kiểm tra kết nối Neo4j thông qua Backend.')) ?></p></div></div>
<?php endif; ?>
<div class="friends-list card">
  <?php foreach ($friends as $person): $n = ($person['full_name'] ?? '') ?: ($person['username'] ?? 'Thành viên'); ?>
    <a class="friend-row" href="profile.php?user_id=<?= e($person['user_id']) ?>"><span class="avatar"><?= e(initial($n)) ?></span><span class="friend-name"><strong><?= e($n) ?></strong><small>@<?= e($person['username'] ?? 'member') ?></small></span><span class="friend-arrow">↗</span></a>
  <?php endforeach; ?>
  <?php if (!$friends): ?><div class="list-empty">Danh sách bạn bè sẽ xuất hiện tại đây.</div><?php endif; ?>
</div>
<?php renderFooter(); ?>
