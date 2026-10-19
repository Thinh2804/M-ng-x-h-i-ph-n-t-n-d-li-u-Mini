<?php /* Dashboard giám sát cluster + benchmark */
[$h, ]  = api('GET', '/admin/health');
[$d, ]  = api('GET', '/admin/shard-distribution');
$bench  = null;
if (isset($_GET['bench'])) {
    [$bench, ] = api('GET', '/admin/benchmark?runs=20');
}

function badge(bool $ok): string {
    return $ok ? '<span class="badge ok">HOẠT ĐỘNG</span>' : '<span class="badge down">MẤT KẾT NỐI</span>';
}
?>
<div class="card">
  <h3>🖥️ Trạng thái các nút</h3>
  <table>
    <tr><th>Thành phần</th><th>Nút</th><th>Trạng thái</th></tr>
    <tr><td>MongoDB Cluster (mongos)</td><td>PC4</td><td><?= badge(!empty($h['mongo_cluster'])) ?></td></tr>
    <?php foreach (($h['shards']['shards'] ?? []) as $s): ?>
      <tr><td>Shard <?= e($s['id']) ?></td><td><?= e($s['host']) ?></td><td><span class="badge ok">ĐÃ ĐĂNG KÝ</span></td></tr>
    <?php endforeach; ?>
    <tr><td>Neo4j (đồ thị)</td><td>PC4</td><td><?= badge(!empty($h['neo4j'])) ?></td></tr>
  </table>
  <p class="meta" style="margin-top:8px">
    Outbox chờ đồng bộ sang Neo4j: <strong><?= (int)($h['outbox_pending'] ?? 0) ?></strong> bản ghi
  </p>
</div>

<div class="card">
  <h3>📊 Phân bố dữ liệu trên các shard</h3>
  <table>
    <tr><th>Collection</th><th>Tổng</th><th>Theo shard</th></tr>
    <?php foreach ($d as $coll => $info): ?>
      <tr>
        <td><?= e($coll) ?></td>
        <td><?= (int)($info['total'] ?? 0) ?></td>
        <td class="meta">
          <?php foreach (($info['per_shard'] ?? []) as $shard => $cnt): ?>
            <?= e($shard) ?>: <strong><?= (int)$cnt ?></strong> &nbsp;
          <?php endforeach; ?>
        </td>
      </tr>
    <?php endforeach; ?>
  </table>
</div>

<div class="card">
  <h3>⏱️ Benchmark truy vấn</h3>
  <a href="index.php?page=admin&bench=1"><button>Chạy benchmark (20 lần/loại)</button></a>
  <?php if ($bench): ?>
    <table style="margin-top:12px">
      <tr><th>Loại truy vấn</th><th>Trung bình (ms)</th><th>P95 (ms)</th><th>Min (ms)</th></tr>
      <?php foreach ($bench as $k => $v): if (!is_array($v)) continue; ?>
        <tr>
          <td><?= e($k) ?></td>
          <td><?= e((string)($v['avg_ms'] ?? '')) ?></td>
          <td><?= e((string)($v['p95_ms'] ?? '')) ?></td>
          <td><?= e((string)($v['min_ms'] ?? '')) ?></td>
        </tr>
      <?php endforeach; ?>
    </table>
  <?php endif; ?>
</div>
