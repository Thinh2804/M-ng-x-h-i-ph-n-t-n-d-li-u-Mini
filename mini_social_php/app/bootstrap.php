<?php
declare(strict_types=1);
if (session_status() !== PHP_SESSION_ACTIVE) {
    session_name('uniconnect_session');
    session_start();
}
$config = require dirname(__DIR__) . '/config.php';
require_once __DIR__ . '/api_client.php';
function e(mixed $value): string { return htmlspecialchars((string)$value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
function currentUser(): array { return $_SESSION['user'] ?? []; }
function isLoggedIn(): bool { return !empty($_SESSION['user']['user_id']); }
function isAdmin(): bool { return strtolower((string)($_SESSION['user']['role'] ?? '')) === 'admin'; }
function requireLogin(): void { if (!isLoggedIn()) { header('Location: login.php'); exit; } }
function requireAdmin(): void { requireLogin(); if (!isAdmin()) { http_response_code(403); exit('Bạn không có quyền truy cập chức năng này.'); } }
function apiPath(string $key, array $replace = []): string {
    global $config;
    $path = $config['api_prefix'] . ($config['endpoints'][$key] ?? '/');
    $replace += ['user_id' => currentUserId()];
    foreach ($replace as $name => $value) $path = str_replace('{' . $name . '}', rawurlencode((string)$value), $path);
    return $path;
}
function currentUserId(): string { return (string)($_SESSION['user']['user_id'] ?? ''); }
// Bảng user_id → user, dùng để hiển thị tên cho các API chỉ trả về ID (vd. danh sách bạn bè)
function userDirectory(): array {
    static $dir = null;
    if ($dir === null) {
        $r = api('GET', apiPath('users'));
        $dir = [];
        foreach (($r['ok'] && is_array($r['data'])) ? $r['data'] : [] as $u) $dir[$u['_id'] ?? ''] = $u;
    }
    return $dir;
}
// Lý do gợi ý kết bạn: bạn chung (Neo4j FRIEND) và/hoặc cùng chủ đề quan tâm (Neo4j INTERESTED_IN)
function suggestionReason(array $p): string {
    $parts = [];
    if (!empty($p['mutual_friends'])) $parts[] = $p['mutual_friends'] . ' bạn chung';
    $label = !empty($p['content_match']) ? 'Bài viết trùng chủ đề: ' : 'Cùng quan tâm: ';
    if (!empty($p['common_topics'])) $parts[] = $label . implode(', ', array_slice($p['common_topics'], 0, 2));
    return $parts ? implode(' · ', $parts) : 'Có thể bạn quen';
}
function initial(string $name): string { return mb_strtoupper(mb_substr($name, 0, 1)); }
// Hiển thị thời gian ISO của API (UTC) theo giờ Việt Nam
function fmtTime(mixed $iso): string {
    if (!$iso) return 'Vừa đăng';
    try { return (new DateTime((string)$iso, new DateTimeZone('UTC')))->setTimezone(new DateTimeZone('Asia/Ho_Chi_Minh'))->format('d/m/Y H:i'); }
    catch (Exception) { return (string)$iso; }
}
function api(string $method, string $path, ?array $body = null): array { return apiRequest($method, $path, $body); }
function flash(string $type, string $message): void { $_SESSION['flash'] = ['type'=>$type, 'message'=>$message]; }
function takeFlash(): ?array { $f = $_SESSION['flash'] ?? null; unset($_SESSION['flash']); return $f; }
