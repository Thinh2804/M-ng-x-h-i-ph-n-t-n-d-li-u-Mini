<?php /* Bảng tin của user đang đăng nhập: Neo4j (bạn bè) + MongoDB (bài viết) */ ?>
<div class="card">
  <h3>📝 Đăng bài mới (lưu MongoDB - shard theo author_id)</h3>
  <form method="post">
    <input type="hidden" name="action" value="create_post">
    <textarea name="content" rows="3" placeholder="Bạn đang nghĩ gì, <?= e($me['username']) ?>?" required></textarea>
    <input name="image_url" placeholder="URL hình ảnh (tùy chọn)">
    <button>Đăng</button>
  </form>
</div>

<?php
[$feed, ] = api('GET', '/social/feed/' . urlencode($me['_id']));
if (!empty($feed['degraded'])): ?>
  <div class="alert card warn">⚠️ Chế độ suy giảm: <?= e($feed['reason'] ?? '') ?> - chỉ hiển thị bài của chính bạn.</div>
<?php else: ?>
  <div class="meta" style="margin-bottom:12px">
    Bảng tin từ <?= (int)($feed['friend_count'] ?? 0) ?> bạn bè (Neo4j) + bài của bạn (MongoDB)
  </div>
<?php endif;

foreach ($feed['posts'] ?? [] as $p): ?>
  <div class="card">
    <strong><?= e($p['author_name'] ?? $p['author_id']) ?></strong>
    <div class="meta"><?= e($p['created_at'] ?? '') ?> · ❤️ <?= (int)($p['likes'] ?? 0) ?></div>
    <p><?= nl2br(e($p['content'])) ?></p>
    <?php foreach ($p['image_urls'] ?? [] as $img): ?>
      <img src="<?= e($img) ?>" style="max-width:100%;border-radius:8px;margin-top:8px">
    <?php endforeach; ?>
    <form method="post" style="display:inline">
      <input type="hidden" name="action" value="like">
      <input type="hidden" name="post_id" value="<?= e($p['_id']) ?>">
      <button>👍 Thích</button>
    </form>
    <?php [$comments, ] = api('GET', '/posts/' . urlencode($p['_id']) . '/comments'); ?>
    <?php foreach ($comments as $cm): ?>
      <div class="meta" style="margin-top:6px">💬 <?= e($cm['content']) ?></div>
    <?php endforeach; ?>
    <form method="post" style="margin-top:8px;display:flex;gap:8px">
      <input type="hidden" name="action" value="comment">
      <input type="hidden" name="post_id" value="<?= e($p['_id']) ?>">
      <input name="content" placeholder="Viết bình luận..." required>
      <button>Gửi</button>
    </form>
  </div>
<?php endforeach;
if (empty($feed['posts'])): ?>
  <div class="card meta">Chưa có bài viết nào - hãy kết bạn hoặc đăng bài đầu tiên.</div>
<?php endif; ?>
