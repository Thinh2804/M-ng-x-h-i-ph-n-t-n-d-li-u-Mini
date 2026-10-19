<?php /* Hồ sơ người dùng đang đăng nhập */
[$profile, ] = api('GET', '/users/' . urlencode($me['_id']));
[$myPosts, ] = api('GET', '/posts/by-author/' . urlencode($me['_id']) . '?limit=50');
[$fr, $fc]   = api('GET', '/social/friends/' . urlencode($me['_id']));
?>
<div class="card">
  <h3>👤 Hồ sơ: <?= e($profile['full_name'] ?: $profile['username']) ?></h3>
  <table>
    <tr><td>Username</td><td><strong><?= e($profile['username']) ?></strong></td></tr>
    <tr><td>Họ tên</td><td><?= e($profile['full_name'] ?? '') ?></td></tr>
    <tr><td>Số bạn bè (Neo4j)</td>
        <td><?= $fc === 200 ? count($fr['friends'] ?? []) : '<span class="badge down">Neo4j down</span>' ?></td></tr>
    <tr><td>Số bài viết (MongoDB)</td><td><?= count($myPosts) ?></td></tr>
    <tr><td>Tham gia</td><td class="meta"><?= e($profile['created_at'] ?? '') ?></td></tr>
  </table>
</div>

<div class="card"><h3>📝 Bài viết của tôi</h3></div>
<?php foreach ($myPosts as $p): ?>
  <div class="card">
    <div class="meta"><?= e($p['created_at'] ?? '') ?> · ❤️ <?= (int)($p['likes'] ?? 0) ?></div>
    <p><?= nl2br(e($p['content'])) ?></p>
  </div>
<?php endforeach;
if (empty($myPosts)): ?>
  <div class="card meta">Bạn chưa có bài viết nào.</div>
<?php endif; ?>
