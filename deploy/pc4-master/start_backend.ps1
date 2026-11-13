# PC4 (MASTER) - Khởi động backend Python + web PHP
$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\..\.."

Write-Host "==> Khoi dong Python API (FastAPI) tren cong 8000..."
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "cd '$root\backend-python'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

Write-Host "==> Khoi dong web PHP (mini_social_php - UniConnect) tren cong 8080..."
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "cd '$root\mini_social_php'; php -S 0.0.0.0:8080 -t public"

# Giao dien cu: giu lai cac trang Dong bo / Cong dong / Benchmark cho bao cao
Write-Host "==> Khoi dong web PHP cu (backend-php) tren cong 8081..."
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "cd '$root\backend-php'; php -S 0.0.0.0:8081 -t public"

Write-Host "==> Xong. Web: http://localhost:8080 | Web cu: http://localhost:8081 | API docs: http://localhost:8000/docs"
