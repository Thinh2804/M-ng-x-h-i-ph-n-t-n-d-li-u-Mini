<?php
function apiRequest(string $method, string $path, ?array $body = null): array {
    global $config;
    if (!function_exists('curl_init')) return ['ok'=>false,'status'=>0,'data'=>null,'error'=>'PHP cURL chưa được bật.'];
    $url = rtrim($config['base_url'], '/') . $path;
    $headers = ['Accept: application/json'];
    $userId = $_SESSION['user']['user_id'] ?? null;
    if ($userId !== null) $headers[] = 'X-User-Id: ' . $userId;
    if (!empty($_SESSION['access_token'])) $headers[] = 'Authorization: Bearer ' . $_SESSION['access_token'];
    $ch = curl_init($url);
    curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER=>true, CURLOPT_CUSTOMREQUEST=>strtoupper($method), CURLOPT_HTTPHEADER=>$headers, CURLOPT_CONNECTTIMEOUT=>3, CURLOPT_TIMEOUT=>(int)$config['timeout']]);
    if ($body !== null) { $headers[] = 'Content-Type: application/json'; curl_setopt($ch, CURLOPT_HTTPHEADER, $headers); curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($body, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE)); }
    $raw = curl_exec($ch); $status = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE); $error = curl_error($ch); curl_close($ch);
    $data = is_string($raw) ? json_decode($raw, true) : null;
    return ['ok'=>$status >= 200 && $status < 300, 'status'=>$status, 'data'=>$data, 'error'=>$error ?: null, 'raw'=>$raw];
}
function apiMessage(array $result, string $fallback): string {
    $status = $result['status'] ?? 0;
    if ($status === 401) return 'Phiên đăng nhập không hợp lệ hoặc đã hết hạn (401). Vui lòng đăng nhập lại.';
    if ($status === 403) return 'Bạn không có quyền thực hiện thao tác này (403).';
    if ($status === 503 || $status === 0) return 'Backend hiện chưa sẵn sàng (503/kết nối thất bại). Vui lòng kiểm tra FastAPI.';
    $detail = $result['data']['detail'] ?? $result['data']['message'] ?? $fallback;
    // FastAPI 422: detail là danh sách lỗi kiểm tra dữ liệu [{loc, msg, ...}]
    if (is_array($detail)) {
        $detail = implode('; ', array_map(fn($d) => is_array($d) ? implode('.', array_slice((array)($d['loc'] ?? []), 1)) . ': ' . ($d['msg'] ?? '') : (string)$d, $detail));
    }
    return (string)$detail;
}
