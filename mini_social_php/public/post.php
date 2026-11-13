<?php
require_once __DIR__ . '/../app/bootstrap.php';
require_once __DIR__ . '/../app/layout.php';
requireLogin();

$pid = (string)($_GET['id'] ?? '');
$r = api('GET', apiPath('post', ['post_id' => $pid]));
$post = $r['ok'] && is_array($r['data']) ? $r['data'] : null;
if ($post) {
    // Ghi nhận "đã xem" 1 lần mỗi phiên → sở thích theo chủ đề bài (Neo4j) → gợi ý người cùng chủ đề
    $_SESSION['viewed'] ??= [];
    if (empty($_SESSION['viewed'][$pid])) {
        $v = api('POST', apiPath('post_view', ['post_id' => $pid]));
        if ($v['ok']) $_SESSION['viewed'][$pid] = true;
    }
}
$dir = userDirectory();
$author = $post ? ($dir[$post['author_id']] ?? []) : [];
$authorName = ($author['full_name'] ?? '') ?: ($author['username'] ?? 'Thành viên');
$c = $post ? api('GET', apiPath('post_comments', ['post_id' => $pid])) : ['ok' => false];
$comments = $c['ok'] && is_array($c['data']) ? $c['data'] : [];

renderHeader('Bài viết', 'feed');
?>
<div class="page-heading"><div><div class="eyebrow">BÀI VIẾT</div><h1>Chi tiết bài viết</h1><p class="muted"><a class="text-link" href="feed.php">← Về bảng tin</a></p></div></div>
<div class="feed-layout">
  <section class="feed-column">
  <?php if (!$post): ?>
    <div class="empty-state card"><div class="empty-art">✧</div><h3>Không tìm thấy bài viết</h3><p><?= e(apiMessage($r, 'Bài viết không tồn tại hoặc đã bị xóa.')) ?></p><a class="btn btn-soft" href="feed.php">Về bảng tin</a></div>
  <?php else: ?>
    <article class="post-card card">
      <div class="post-head">
        <span class="avatar"><?= e(initial($authorName)) ?></span>
        <div class="post-author"><a href="profile.php?user_id=<?= e($post['author_id']) ?>"><strong><?= e($authorName) ?></strong></a><small><?= e(fmtTime($post['created_at'] ?? null)) ?></small></div>
      </div>
      <div class="post-content"><?= nl2br(e($post['content'] ?? '')) ?></div>
      <?php if (!empty($post['image_urls']) && is_array($post['image_urls'])): ?>
        <div class="post-images"><?php foreach (array_slice($post['image_urls'], 0, 4) as $img): ?><img src="<?= e($img) ?>" alt="Ảnh bài viết" loading="lazy"><?php endforeach; ?></div>
      <?php endif; ?>
      <div class="post-stats"><span>♡ <?= e($post['likes'] ?? 0) ?> lượt thích</span><span><?= count($comments) ?> bình luận</span></div>
      <div class="post-actions">
        <form method="post" action="action.php"><input type="hidden" name="post_id" value="<?= e($pid) ?>"><button name="action" value="like" class="post-action">♡ <span>Thích</span></button></form>
      </div>
      <?php if ($comments): ?>
        <ul class="comment-list">
          <?php foreach ($comments as $cm): $cn = ($dir[$cm['author_id'] ?? '']['full_name'] ?? '') ?: ($dir[$cm['author_id'] ?? '']['username'] ?? 'Thành viên'); ?>
            <li><span class="avatar avatar-sm"><?= e(initial($cn)) ?></span><div><strong><?= e($cn) ?></strong><p><?= e($cm['content'] ?? '') ?></p></div></li>
          <?php endforeach; ?>
        </ul>
      <?php endif; ?>
      <form class="comment-form is-open" method="post" action="action.php"><input type="hidden" name="post_id" value="<?= e($pid) ?>"><input name="content" required maxlength="2000" placeholder="Viết bình luận..." aria-label="Viết bình luận"><button name="action" value="comment">Gửi</button></form>
    </article>
  <?php endif; ?>
  </section>
  <aside class="right-rail"><?php renderSuggestionRail(5); ?></aside>
</div>
<?php renderFooter(); ?>
