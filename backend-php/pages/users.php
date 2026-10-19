<?php /* Danh sách người dùng + kết bạn (từ user đang đăng nhập) */
[$myFriends, $fc] = api('GET', '/social/friends/' . urlencode($me['_id']));
$friendIds = $fc === 200 ? ($myFriends['friends'] ?? []) : [];
?>
<div class="card">
  <h3>👥 Danh sách người dùng (<?= count($users) ?>)</h3>
  <?php if ($fc !== 200): ?>
    <div class="alert warn">⚠️ Neo4j (PC4) không khả dụng - không hiển thị được trạng thái bạn bè.</div>
  <?php endif; ?>
  <table>
    <tr><th>Username</th><th>Họ tên</th><th>Số bạn</th><th></th></tr>
    <?php foreach ($users as $u): if ($u['_id'] === $me['_id']) continue; ?>
      <tr>
        <td><strong><?= e($u['username']) ?></strong></td>
        <td><?= e($u['full_name'] ?? '') ?></td>
        <td><?= (int)($u['friend_count'] ?? 0) ?></td>
        <td>
          <?php if (in_array($u['_id'], $friendIds, true)): ?>
            <span class="badge ok">✓ Bạn bè</span>
          <?php else: ?>
            <form method="post" style="display:inline">
              <input type="hidden" name="action" value="add_friend">
              <input type="hidden" name="to_user" value="<?= e($u['_id']) ?>">
              <button>Kết bạn</button>
            </form>
          <?php endif; ?>
        </td>
      </tr>
    <?php endforeach; ?>
  </table>
</div>
