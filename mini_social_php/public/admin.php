<?php
require_once __DIR__ . '/../app/bootstrap.php';
require_once __DIR__ . '/../app/layout.php';
requireAdmin();

$h = api('GET', apiPath('health'));
$d = api('GET', apiPath('shards'));
$health = $h['ok'] && is_array($h['data']) ? $h['data'] : [];
$dist = $d['ok'] && is_array($d['data']) ? $d['data'] : [];
$shards = $health['shards']['shards'] ?? [];
$mongoOk = !empty($health['mongo_cluster']);
$neoOk = !empty($health['neo4j']);
$pending = $health['outbox_pending'] ?? null;
$collections = ['posts' => 'Bài viết', 'comments' => 'Bình luận', 'users' => 'Người dùng'];

renderHeader('Giám sát hệ thống', 'admin');
?>
<div class="page-heading"><div><div class="eyebrow">ADMIN CONTROL CENTER</div><h1>Giám sát hệ thống</h1><p class="muted">Theo dõi sức khỏe dịch vụ và tình trạng dữ liệu phân tán.</p></div><a class="btn btn-soft" href="admin.php">↻ Làm mới</a></div>
<?php if (!$h['ok'] || !$d['ok']): ?>
  <div class="backend-notice"><span class="notice-icon">!</span><div><strong>Chưa lấy đủ dữ liệu giám sát</strong><p><?= e(apiMessage($h['ok'] ? $d : $h, 'Kiểm tra các API Admin trong FastAPI.')) ?></p></div></div>
<?php endif; ?>

<div class="admin-summary">
  <article class="metric-card card"><div class="metric-top"><span>MONGODB CLUSTER</span><span class="metric-icon">⌁</span></div><strong class="metric-value"><?= $mongoOk ? 'Hoạt động' : 'Mất kết nối' ?></strong><span class="metric-foot"><i class="status-dot <?= $mongoOk ? 'online' : 'offline' ?>"></i>mongos (PC4)</span></article>
  <article class="metric-card card"><div class="metric-top"><span>MONGODB SHARDS</span><span class="metric-icon">▤</span></div><strong class="metric-value"><?= count($shards) ?></strong><span class="metric-foot">Shard trong cluster</span></article>
  <article class="metric-card card"><div class="metric-top"><span>OUTBOX PENDING</span><span class="metric-icon">◷</span></div><strong class="metric-value"><?= e($pending === null || $pending < 0 ? '—' : $pending) ?></strong><span class="metric-foot">Sự kiện chờ đồng bộ sang Neo4j</span></article>
  <article class="metric-card card"><div class="metric-top"><span>NEO4J</span><span class="metric-icon">⌘</span></div><strong class="metric-value"><?= $h['ok'] ? ($neoOk ? 'Hoạt động' : 'Mất kết nối') : '—' ?></strong><span class="metric-foot"><i class="status-dot <?= $neoOk ? 'online' : 'offline' ?>"></i>Graph database (PC4)</span></article>
</div>

<div class="admin-grid">
  <section class="card admin-panel">
    <div class="panel-heading"><div><h2>MongoDB Sharded Cluster</h2><p class="muted">Số document mỗi shard đang giữ</p></div><span class="panel-tag">DATABASE</span></div>
    <div class="shard-list">
      <?php foreach ($shards as $shard):
          $sid = $shard['id'] ?? 'shard';
          $ok = (int)($shard['state'] ?? 0) === 1;
          $parts = [];
          foreach ($collections as $coll => $label) $parts[] = $label . ': ' . ($dist[$coll]['per_shard'][$sid] ?? 0);
      ?>
      <div class="shard-row"><span class="shard-symbol">▤</span><div class="shard-info"><strong><?= e($sid) ?></strong><small><?= e($shard['host'] ?? '') ?></small><small><?= e(implode(' · ', $parts)) ?></small></div><span class="status-label <?= $ok ? 'good' : 'neutral' ?>"><?= $ok ? 'Healthy' : 'Unknown' ?></span></div>
      <?php endforeach; ?>
      <?php if (!$shards): ?><div class="list-empty">Chưa có dữ liệu Shard từ API.</div><?php endif; ?>
    </div>
  </section>
  <section class="card admin-panel">
    <div class="panel-heading"><div><h2>Phân bố dữ liệu</h2><p class="muted">Tổng document và tỷ lệ trên từng shard</p></div><span class="panel-tag">SHARDING</span></div>
    <div class="outbox-numbers">
      <?php foreach ($collections as $coll => $label): ?>
        <div><strong><?= e($dist[$coll]['total'] ?? '—') ?></strong><span><?= e($label) ?></span></div>
      <?php endforeach; ?>
    </div>
    <?php foreach ($collections as $coll => $label): $total = max(1, (int)($dist[$coll]['total'] ?? 0)); $per = $dist[$coll]['per_shard'] ?? []; ksort($per); // cùng thứ tự → cùng màu cho mỗi shard ?>
      <div class="dist-row"><span><?= e($label) ?></span><div class="dist-bar">
        <?php $i = 0; foreach ($per as $sid => $n): ?>
          <i class="seg-<?= $i++ % 2 ?>" style="width:<?= round($n * 100 / $total, 1) ?>%" title="<?= e("$sid: $n") ?>"><?= e("$sid " . round($n * 100 / $total) . '%') ?></i>
        <?php endforeach; ?>
      </div></div>
    <?php endforeach; ?>
    <form method="post" action="action.php" class="outbox-note"><span>Outbox: <?= e($pending ?? '—') ?> sự kiện chờ đồng bộ MongoDB → Neo4j.</span> <button class="btn btn-soft" name="action" value="process_outbox">Xử lý outbox</button></form>
  </section>
</div>
<section class="card health-detail"><div class="panel-heading"><div><h2>Health Check chi tiết</h2><p class="muted">Phản hồi của GET /admin/health</p></div><span class="panel-tag">LIVE STATUS</span></div><pre><?= e(json_encode($health, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) ?: '{}') ?></pre></section>
<?php renderFooter(); ?>
