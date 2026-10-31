# PC4 - Khởi động bản sao thứ 3 của rs1 và rs2 (chạy trước scripts\init_cluster.ps1)
$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path C:\data\rs1-secondary, C:\data\rs2-secondary, C:\data\log | Out-Null

Write-Host "==> Khoi dong ban sao rs1 (cong 27038) chay nen..."
Start-Process mongod -ArgumentList "--config", "`"$PSScriptRoot\rs1-secondary.cfg`""

Write-Host "==> Khoi dong ban sao rs2 (cong 27039) chay nen..."
Start-Process mongod -ArgumentList "--config", "`"$PSScriptRoot\rs2-secondary.cfg`""
