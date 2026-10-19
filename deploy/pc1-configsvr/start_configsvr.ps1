# PC1 - Khởi động Config Server (chạy PowerShell với quyền Administrator)
$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path C:\data\configsvr, C:\data\log | Out-Null

Write-Host "==> Khoi dong Config Server (cfgrs) tren cong 27019..."
mongod --config "$PSScriptRoot\configsvr.cfg"
