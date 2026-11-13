<?php
require_once __DIR__ . '/../app/bootstrap.php';
require_once __DIR__ . '/../app/layout.php';
requireLogin();

$q = trim($_GET['q'] ?? '');
if ($q !== '') {
    // Tìm kiếm không có shard key → mongos quét mọi shard (scatter-gather)
    $feed = api('GET', apiPath('search', ['q' => $q]));
    $posts = $feed['ok'] && is_array($feed['data']) ? $feed['data'] : [];
    $dir = userDirectory();
    foreach ($posts as &$p) {
        $a = $dir[$p['author_id'] ?? ''] ?? [];
        $p['author_name'] = $a['full_name'] ?? $a['username'] ?? 'Thành viên';
    }
    unset($p);
} else {
    $feed = api('GET', apiPath('feed'));
    $posts = $feed['ok'] ? ($feed['data']['posts'] ?? []) : [];
}
if (!is_array($posts)) $posts = [];
$degraded = !empty($feed['data']['degraded']);

// Bình luận của từng bài (collection comments, shard theo post_id)
$comments = [];
foreach ($posts as $post) {
    $pid = $post['_id'] ?? '';
    $c = api('GET', apiPath('post_comments', ['post_id' => $pid]));
    $comments[$pid] = $c['ok'] && is_array($c['data']) ? $c['data'] : [];
}
$dir = $comments && array_filter($comments) ? userDirectory() : [];
$me = currentUser();

renderHeader('Bảng tin', 'feed');
?>
<div class="page-heading">
  <div>
    <div class="eyebrow">KHÔNG GIAN CỦA BẠN</div>
    <?php if ($q !== ''): ?>
      <h1>Kết quả tìm kiếm</h1>
      <p class="muted"><?= count($posts) ?> bài viết chứa “<?= e($q) ?>” · <a class="text-link" href="feed.php">Về bảng tin</a></p>
    <?php else: ?>
      <h1>Bảng tin <span class="heading-spark">✦</span></h1>
      <p class="muted">Bài viết của bạn và <?= e($feed['data']['friend_count'] ?? 0) ?> bạn bè.</p>
    <?php endif; ?>
  </div>
  <div class="date-chip"><span>◷</span> Hôm nay</div>
</div>

<?php if (!$feed['ok']): ?>
  <div class="backend-notice"><span class="notice-icon">!</span><div><strong>Chưa kết nối được Backend</strong><p><?= e(apiMessage($feed, 'Không tải được bảng tin.')) ?></p></div></div>
<?php elseif ($degraded): ?>
  <div class="backend-notice"><span class="notice-icon">!</span><div><strong>Neo4j tạm thời không khả dụng</strong><p><?= e(($feed['data']['reason'] ?? 'Neo4j') . ' - chỉ hiển thị bài viết của bạn cho tới khi đồ thị bạn bè hoạt động lại.') ?></p></div></div>
<?php endif; ?>

<div class="feed-layout">
  <section class="feed-column">
    <?php if ($q === ''): ?>
    <form class="composer card" method="post" action="action.php">
      <div class="composer-top">
        <span class="avatar avatar-lg"><?= e(initial($me['full_name'] ?? $me['username'] ?? 'U')) ?></span>
        <label class="composer-input"><textarea name="content" required maxlength="5000" placeholder="Bạn đang nghĩ gì? Chia sẻ với mọi người..."></textarea></label>
      </div>
      <div class="composer-bottom">
        <span class="composer-hint">✧ Một điều tích cực để chia sẻ hôm nay?</span>
        <button class="btn btn-primary" name="action" value="create_post">Đăng bài <span>↗</span></button>
      </div>
    </form>
    <?php endif; ?>

    <?php foreach ($posts as $post):
        $authorName = $post['author_name'] ?? 'Thành viên';
        $pid = $post['_id'] ?? '';
        $postComments = $comments[$pid] ?? [];
    ?>
    <article class="post-card card">
      <div class="post-head">
        <span class="avatar"><?= e(initial($authorName)) ?></span>
        <div class="post-author">
          <a href="profile.php?user_id=<?= e($post['author_id'] ?? '') ?>"><strong><?= e($authorName) ?></strong></a>
          <a href="post.php?id=<?= e($pid) ?>"><small><?= e(fmtTime($post['created_at'] ?? null)) ?></small></a>
        </div>
      </div>
      <a class="post-content post-link" href="post.php?id=<?= e($pid) ?>"><?= nl2br(e($post['content'] ?? '')) ?></a>
      <?php if (!empty($post['image_urls']) && is_array($post['image_urls'])): ?>
        <div class="post-images"><?php foreach (array_slice($post['image_urls'], 0, 4) as $img): ?><img src="<?= e($img) ?>" alt="Ảnh bài viết" loading="lazy"><?php endforeach; ?></div>
      <?php endif; ?>
      <div class="post-stats"><span>♡ <?= e($post['likes'] ?? 0) ?> lượt thích</span><span><?= count($postComments) ?> bình luận</span></div>
      <div class="post-actions">
        <form method="post" action="action.php"><input type="hidden" name="post_id" value="<?= e($pid) ?>"><button name="action" value="like" class="post-action">♡ <span>Thích</span></button></form>
        <button type="button" class="post-action comment-toggle">▢ <span>Bình luận</span></button>
      </div>
      <?php if ($postComments): ?>
        <ul class="comment-list">
          <?php foreach ($postComments as $c): $cn = $dir[$c['author_id'] ?? '']['full_name'] ?? $dir[$c['author_id'] ?? '']['username'] ?? 'Thành viên'; ?>
            <li><span class="avatar avatar-sm"><?= e(initial($cn)) ?></span><div><strong><?= e($cn) ?></strong><p><?= e($c['content'] ?? '') ?></p></div></li>
          <?php endforeach; ?>
        </ul>
      <?php endif; ?>
      <form class="comment-form" method="post" action="action.php"><input type="hidden" name="post_id" value="<?= e($pid) ?>"><input name="content" required maxlength="2000" placeholder="Viết bình luận..." aria-label="Viết bình luận"><button name="action" value="comment">Gửi</button></form>
    </article>
    <?php endforeach; ?>

    <?php if (!$posts): ?>
      <div class="empty-state card"><div class="empty-art">✧</div>
        <h3><?= $q !== '' ? 'Không tìm thấy bài viết phù hợp' : 'Bảng tin đang chờ câu chuyện đầu tiên' ?></h3>
        <p><?= $q !== '' ? 'Thử từ khóa khác.' : 'Hãy đăng bài viết đầu tiên hoặc kết nối thêm bạn bè để làm mới bảng tin.' ?></p>
      </div>
    <?php endif; ?>
  </section>
  <aside class="right-rail">
    <?php renderSuggestionRail(); ?>
    <div class="rail-card card"><div class="rail-title">Về UniConnect</div><p>Bài viết lưu trên MongoDB Sharded Cluster, quan hệ bạn bè trên Neo4j.</p><div class="rail-tags"><span>Chia sẻ</span><span>Kết nối</span><span>Cộng đồng</span></div></div>
  </aside>
</div>
<?php renderFooter(); ?>
