<?php
function renderHeader(string $title, string $active = ''): void {
    $user = currentUser(); $name = $user['full_name'] ?? $user['username'] ?? 'Thành viên'; $initial = mb_strtoupper(mb_substr($name,0,1));
    ?>
<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title><?=e($title)?> · UniConnect</title><link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Manrope:wght@500;600;700;800&display=swap" rel="stylesheet"><link rel="stylesheet" href="assets/css/style.css"></head><body>
    <header class="topbar"><a class="brand" href="feed.php"><span class="brand-mark">u</span><span>Uni<span class="brand-accent">Connect</span></span></a><div class="top-search"><span>⌕</span><input id="globalSearch" placeholder="Tìm bài viết trên UniConnect..."></div><div class="top-actions"><button class="icon-btn" aria-label="Thông báo">♧<i></i></button><a class="user-chip" href="profile.php"><span class="avatar avatar-sm"><?=e($initial)?></span><span><?=e($name)?></span></a></div></header>
    <div class="app-shell"><aside class="sidebar"><div class="side-label">KHÔNG GIAN CỦA BẠN</div><a class="nav-item <?=$active==='feed'?'active':''?>" href="feed.php"><span>⌂</span>Bảng tin</a><a class="nav-item <?=$active==='friends'?'active':''?>" href="friends.php"><span>♧</span>Bạn bè</a><a class="nav-item <?=$active==='profile'?'active':''?>" href="profile.php"><span>◎</span>Trang cá nhân</a><?php if(isAdmin()): ?><div class="side-label side-gap">QUẢN TRỊ</div><a class="nav-item <?=$active==='admin'?'active':''?>" href="admin.php"><span>▦</span>Giám sát hệ thống</a><?php endif; ?><div class="sidebar-bottom"><div class="mini-help"><div class="help-icon">✦</div><strong>Kết nối mỗi ngày</strong><p>Chia sẻ câu chuyện và giữ liên lạc với bạn bè.</p></div><a class="nav-item logout" href="logout.php"><span>↪</span>Đăng xuất</a><div class="side-foot">UniConnect · Mini Social Network</div></div></aside><main class="main-content">
    <?php if ($f=takeFlash()): ?><div class="alert alert-<?=e($f['type'])?>"><?=e($f['message'])?></div><?php endif; ?>
    <?php
}
// Khung "Gợi ý cho bạn" ở cột phải: top gợi ý kết bạn kèm lý do và nút kết bạn
function renderSuggestionRail(int $limit = 3): void {
    $r = api('GET', apiPath('suggestions'));
    $list = array_slice($r['ok'] ? ($r['data']['suggestions'] ?? []) : [], 0, $limit);
    ?><div class="rail-card card"><div class="rail-title"><span>✦</span> Gợi ý cho bạn</div>
    <?php if (!$list): ?><p>Đăng bài hoặc xem bài viết bạn thích để nhận gợi ý những người cùng chủ đề.</p>
    <?php else: ?><ul class="rail-people"><?php foreach ($list as $p): $n = ($p['full_name'] ?? '') ?: ($p['username'] ?? 'Thành viên'); ?>
      <li><a class="avatar avatar-sm" href="profile.php?user_id=<?= e($p['user_id']) ?>"><?= e(initial($n)) ?></a><div><a href="profile.php?user_id=<?= e($p['user_id']) ?>"><strong><?= e($n) ?></strong></a><small><?= e(suggestionReason($p)) ?></small></div>
      <form method="post" action="action.php"><input type="hidden" name="user_id" value="<?= e($p['user_id']) ?>"><button name="action" value="add_friend" title="Kết bạn">＋</button></form></li>
    <?php endforeach; ?></ul><?php endif; ?>
    <a class="text-link" href="friends.php">Xem tất cả gợi ý →</a></div><?php
}
function renderFooter(): void { ?><footer class="mobile-footer"><a href="feed.php">⌂<small>Bảng tin</small></a><a href="friends.php">♧<small>Bạn bè</small></a><a href="profile.php">◎<small>Cá nhân</small></a><?php if(isAdmin()): ?><a href="admin.php">▦<small>Quản trị</small></a><?php endif; ?></footer></main></div><script src="assets/js/app.js"></script></body></html><?php }
