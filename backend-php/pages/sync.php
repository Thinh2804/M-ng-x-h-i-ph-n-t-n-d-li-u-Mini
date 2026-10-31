<?php /* Đối chiếu từng user giữa MongoDB và Neo4j - chỉ admin */
[$sync, ] = api('GET', '/admin/sync-view');
$rows = $sync['rows'] ?? [];
$matched = count(array_filter($rows, fn($r) => !empty($r['synced'])));
?>
<div class="card">
  <h3>🔄 Đồng bộ MongoDB ↔ Neo4j</h3>
  <p class="meta">Hai CSDL nối với nhau qua khóa <strong>users._id</strong> (MongoDB) = <strong>User.id</strong> (Neo4j).</p>
  <?php if (empty($sync['neo4j_ok'])): ?>
    <div class="alert warn">⚠️ Không đọc được Neo4j nên chưa đối chiếu được. Outbox chờ đồng bộ: <?= (int)($sync['outbox_pending'] ?? 0) ?> bản ghi.</div>
  <?php else: ?>
    <p>
      <span class="badge <?= $matched === count($rows) ? 'ok' : 'down' ?>"><?= $matched ?>/<?= count($rows) ?> người dùng khớp</span>
      &nbsp;Outbox chờ đồng bộ: <strong><?= (int)($sync['outbox_pending'] ?? 0) ?></strong>
    </p>
  <?php endif; ?>
</div>

<?php if ($rows): ?>
<div class="card" style="overflow-x:auto">
  <table>
    <tr>
      <th>ID (khóa nối)</th>
      <th>Username<br><span class="meta">Mongo / Neo4j</span></th>
      <th>Họ tên<br><span class="meta">Mongo / Neo4j</span></th>
      <th>Số bạn<br><span class="meta">Mongo / Neo4j</span></th>
      <th>Bài viết<br><span class="meta">Mongo</span></th>
      <th>Trạng thái</th>
    </tr>
    <?php foreach ($rows as $r): $m = $r['mongo'] ?? null; $g = $r['neo4j'] ?? null; ?>
      <tr>
        <td class="meta" title="<?= e($r['id']) ?>"><?= e(substr($r['id'], 0, 8)) ?>…</td>
        <td><?= e($m['username'] ?? '—') ?> / <?= e($g['username'] ?? '—') ?></td>
        <td><?= e($m['full_name'] ?? '—') ?> / <?= e($g['full_name'] ?? '—') ?></td>
        <td><?= $m ? (int)($m['friend_count'] ?? 0) : '—' ?> / <?= $g ? (int)$g['friends'] : '—' ?></td>
        <td><?= (int)$r['posts'] ?></td>
        <td><span class="badge <?= !empty($r['synced']) ? 'ok' : 'down' ?>"><?= !empty($r['synced']) ? 'KHỚP' : 'LỆCH' ?></span></td>
      </tr>
    <?php endforeach; ?>
  </table>
</div>
<?php endif; ?>
