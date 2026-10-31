# PC3 - Khởi động Shard 2 primary + secondary của rs1 (minh họa sao chép)
$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path C:\data\shard2, C:\data\shard1-secondary, C:\data\configsvr, C:\data\log | Out-Null

Write-Host "==> Khoi dong config server (cong 27019) chay nen..."
Start-Process mongod -ArgumentList "--config", "`"$PSScriptRoot\configsvr.cfg`""

Write-Host "==> Khoi dong secondary rs1 (cong 27028) chay nen..."
Start-Process mongod -ArgumentList "--config", "`"$PSScriptRoot\shard1-secondary.cfg`""

Write-Host "==> Khoi dong Shard 2 primary (rs2) tren cong 27018..."
mongod --config "$PSScriptRoot\shard2.cfg"
