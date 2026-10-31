# PC2 - Khởi động Shard 1 primary + secondary của rs2 (minh họa sao chép)
$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path C:\data\shard1, C:\data\shard2-secondary, C:\data\configsvr, C:\data\log | Out-Null

Write-Host "==> Khoi dong config server (cong 27019) chay nen..."
Start-Process mongod -ArgumentList "--config", "`"$PSScriptRoot\configsvr.cfg`""

Write-Host "==> Khoi dong secondary rs2 (cong 27029) chay nen..."
Start-Process mongod -ArgumentList "--config", "`"$PSScriptRoot\shard2-secondary.cfg`""

Write-Host "==> Khoi dong Shard 1 primary (rs1) tren cong 27018..."
mongod --config "$PSScriptRoot\shard1.cfg"
