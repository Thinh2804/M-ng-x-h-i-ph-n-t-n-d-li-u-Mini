<?php /* Phát hiện cộng đồng từ Neo4j */
[$res, ] = api('GET', '/social/communities'); ?>
<div class="card">
  <h3>🏘️ Cộng đồng (thành phần liên thông trong đồ thị bạn bè - Neo4j)</h3>
</div>
<?php if (!empty($res['degraded'])): ?>
  <div class="alert card warn">⚠️ <?= e($res['reason'] ?? 'Neo4j không khả dụng') ?></div>
<?php endif;
foreach ($res['communities'] ?? [] as $i => $c): ?>
  <div class="card">
    <strong>Cộng đồng #<?= $i + 1 ?></strong>
    <div class="meta"><?= (int)$c['size'] ?> thành viên</div>
    <p class="meta"><?= e(implode(', ', array_slice($c['members'], 0, 10))) ?><?= $c['size'] > 10 ? '…' : '' ?></p>
  </div>
<?php endforeach; ?>
