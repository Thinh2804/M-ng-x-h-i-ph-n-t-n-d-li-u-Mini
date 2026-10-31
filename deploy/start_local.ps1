# Chạy toàn bộ trên 1 máy: Python API (:8000) + web PHP (:8080).
# Cần MongoDB service và Neo4j DBMS đang chạy trước.
$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."

$php = (Get-Command php -ErrorAction SilentlyContinue).Source
if (-not $php) {
    $php = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\PHP.PHP.8.4_Microsoft.Winget.Source_8wekyb3d8bbwe\php.exe"
}
# winget symlink: lấy thư mục thật để tìm ext\php_curl.dll
$phpReal = (Get-Item $php).Target
if ($phpReal) { $php = $phpReal }
$phpExt = Join-Path (Split-Path $php) "ext"

Write-Host "==> Khoi dong Python API (FastAPI) tren cong 8000..."
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "cd '$root\backend-python'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

Write-Host "==> Khoi dong PHP web tren cong 8080..."
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "cd '$root\backend-php'; & '$php' -d extension_dir='$phpExt' -d extension=curl -S 127.0.0.1:8080 -t public"

Write-Host "==> Xong. Web: http://localhost:8080 | API docs: http://localhost:8000/docs"
