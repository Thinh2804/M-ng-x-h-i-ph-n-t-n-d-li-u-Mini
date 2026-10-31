# PC4 (MASTER) - Khởi động mongos router, cổng 27017
# Yêu cầu: đã cài MongoDB Community Server + đã chạy scripts/init_cluster.ps1 bước 1
$ErrorActionPreference = "Stop"

# Đọc IP các máy từ .env
$envFile = Join-Path $PSScriptRoot "..\..\.env"
Get-Content $envFile | Where-Object { $_ -match '^\s*[^#].*=' } | ForEach-Object {
    $k, $v = $_ -split '=', 2
    Set-Item -Path "env:$($k.Trim())" -Value $v.Trim()
}

New-Item -ItemType Directory -Force -Path C:\data\log | Out-Null

Write-Host "==> Khoi dong mongos (cong 27017), configdb = cfgrs tren PC1, PC2, PC3..."
mongos --configdb "cfgrs/$($env:PC1_IP):27019,$($env:PC2_IP):27019,$($env:PC3_IP):27019" --port 27017 --bind_ip_all `
       --logpath C:\data\log\mongos.log --logappend
