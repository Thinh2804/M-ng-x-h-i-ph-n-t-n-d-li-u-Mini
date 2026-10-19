<?php /* Gợi ý kết bạn cho user đang đăng nhập: Neo4j FoF + MongoDB enrich */
[$res, ] = api('GET', '/social/suggestions/' . urlencode($me['_id']));
?>
<div class="card">
  <h3>💡 Gợi ý kết bạn cho <?= e($me['username']) ?></h3>
  <p class="meta">Friend-of-friend từ Neo4j (PC4) + hồ sơ/số bài viết từ MongoDB (shard PC2, PC3)</p>
</div>

<?php if (!empty($res['degraded'])): ?>
  <div class="alert card warn">⚠️ <?= e($res['reason'] ?? 'Neo4j không khả dụng') ?></div>
<?php endif;
foreach ($res['suggestions'] ?? [] as $s): ?>
  <div class="card">
    <strong><?= e($s['username'] ?? $s['user_id']) ?></strong>
    <?= e($s['full_name'] ?? '') ?>
    <div class="meta">
      <?= (int)$s['mutual_friends'] ?> bạn chung (Neo4j) ·
      <?= (int)($s['post_count'] ?? 0) ?> bài viết (MongoDB)
    </div>
    <form method="post">
      <input type="hidden" name="action" value="add_friend">
      <input type="hidden" name="to_user" value="<?= e($s['user_id']) ?>">
      <button>Kết bạn</button>
    </form>
  </div>
<?php endforeach;
if (empty($res['suggestions']) && empty($res['degraded'])): ?>
  <div class="card meta">Chưa có gợi ý - hãy kết bạn thêm để có bạn chung.</div>
<?php endif; ?>
