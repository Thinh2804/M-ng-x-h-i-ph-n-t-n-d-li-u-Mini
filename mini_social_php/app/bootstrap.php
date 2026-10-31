<?php
require_once dirname(__DIR__) . '/config.php';
if (session_status() !== PHP_SESSION_ACTIVE) { session_start(); }
function e($value): string { return htmlspecialchars((string)($value ?? ''), ENT_QUOTES, 'UTF-8'); }
function currentUser(): ?array { return $_SESSION[SESSION_USER_KEY] ?? null; }
function requireLogin(): void { if (!currentUser()) { header('Location: login.php'); exit; } }
function requireAdmin(): void { requireLogin(); if ((currentUser()['role'] ?? '') !== 'admin') { http_response_code(403); exit('403 - Bạn không có quyền truy cập trang quản trị.'); } }
function apiRequest(string $method, string $path, ?array $payload = null, bool $authenticated = true): array {
    $url = rtrim(API_BASE_URL, '/') . '/' . ltrim($path, '/');
    $headers = ['Accept: application/json'];
    if ($authenticated && currentUser()) { $headers[] = 'X-User-Id: ' . (currentUser()['_id'] ?? ''); }
    if ($payload !== null) { $headers[] = 'Content-Type: application/json'; }
    $ch = curl_init($url);
    curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_CUSTOMREQUEST => strtoupper($method), CURLOPT_HTTPHEADER => $headers, CURLOPT_TIMEOUT => 12]);
    if ($payload !== null) { curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload, JSON_UNESCAPED_UNICODE)); }
    $body = curl_exec($ch); $error = curl_error($ch); $status = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE); curl_close($ch);
    $data = is_string($body) ? json_decode($body, true) : null;
    if ($error) return ['ok'=>false, 'status'=>0, 'data'=>null, 'message'=>'Không thể kết nối Backend: '.$error];
    return ['ok'=>$status >= 200 && $status < 300, 'status'=>$status, 'data'=>$data, 'message'=>$data['detail'] ?? $data['message'] ?? ($status ? 'HTTP '.$status : 'Không có phản hồi')];
}
function flash(string $type, string $message): void { $_SESSION['flash'] = ['type'=>$type, 'message'=>$message]; }
function takeFlash(): ?array { $f=$_SESSION['flash'] ?? null; unset($_SESSION['flash']); return $f; }
