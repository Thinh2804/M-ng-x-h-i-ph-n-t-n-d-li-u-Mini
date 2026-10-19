<?php
// Cấu hình - trỏ tới Python API trên PC4 (master)
define('API_BASE', getenv('API_BASE') ?: 'http://127.0.0.1:8000');

/** Gọi Python API bằng cURL, tự gắn X-User-Id từ session. Trả về [data, httpCode]. */
function api(string $method, string $path, ?array $body = null): array
{
    $headers = ['Content-Type: application/json'];
    if (!empty($_SESSION['user']['_id'])) {
        $headers[] = 'X-User-Id: ' . $_SESSION['user']['_id'];
    }
    $ch = curl_init(API_BASE . $path);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CUSTOMREQUEST  => $method,
        CURLOPT_TIMEOUT        => 10,
        CURLOPT_HTTPHEADER     => $headers,
    ]);
    if ($body !== null) {
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($body, JSON_UNESCAPED_UNICODE));
    }
    $res  = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($res === false) {
        return [['detail' => 'Không kết nối được Python API (PC4)'], 0];
    }
    return [json_decode($res, true) ?? [], $code];
}

function e(?string $s): string
{
    return htmlspecialchars($s ?? '', ENT_QUOTES, 'UTF-8');
}
