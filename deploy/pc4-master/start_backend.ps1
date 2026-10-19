# PC4 (MASTER) - Khởi động backend Python + web PHP
$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\..\.."

Write-Host "==> Khoi dong Python API (FastAPI) tren cong 8000..."
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "cd '$root\backend-python'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

Write-Host "==> Khoi dong PHP web tren cong 8080..."
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "cd '$root\backend-php'; php -S 0.0.0.0:8080 -t public"

Write-Host "==> Xong. Web: http://localhost:8080 | API docs: http://localhost:8000/docs"
