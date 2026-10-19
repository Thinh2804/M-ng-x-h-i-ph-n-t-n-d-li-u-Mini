# Khởi tạo MongoDB Sharded Cluster - chạy trên PC4 (máy quản trị, đã cài mongosh).
# Thứ tự trước đó: PC1 chạy start_configsvr.ps1, PC2/PC3 chạy start_shard*.ps1,
# PC4 chạy start_mongos.ps1 (sau bước 1 bên dưới).
$ErrorActionPreference = "Stop"
$envFile = Join-Path $PSScriptRoot "..\.env"
Get-Content $envFile | Where-Object { $_ -match '^\s*[^#].*=' } | ForEach-Object {
    $k, $v = $_ -split '=', 2
    Set-Item -Path "env:$($k.Trim())" -Value $v.Trim()
}

Write-Host "==> 1. Khoi tao config replica set (cfgrs) tren PC1"
mongosh --host $env:PC1_IP --port 27019 --eval @"
rs.initiate({
  _id: 'cfgrs', configsvr: true,
  members: [ { _id: 0, host: '$($env:PC1_IP):27019' } ]
})
"@

Write-Host "==> 2. Khoi tao rs1 (Shard 1: primary PC2, secondary PC3 - minh hoa sao chep)"
mongosh --host $env:PC2_IP --port 27018 --eval @"
rs.initiate({
  _id: 'rs1',
  members: [
    { _id: 0, host: '$($env:PC2_IP):27018', priority: 2 },
    { _id: 1, host: '$($env:PC3_IP):27028', priority: 1 }
  ]
})
"@

Write-Host "==> 3. Khoi tao rs2 (Shard 2: primary PC3, secondary PC2 - minh hoa sao chep)"
mongosh --host $env:PC3_IP --port 27018 --eval @"
rs.initiate({
  _id: 'rs2',
  members: [
    { _id: 0, host: '$($env:PC3_IP):27018', priority: 2 },
    { _id: 1, host: '$($env:PC2_IP):27029', priority: 1 }
  ]
})
"@

Write-Host "==> Cho 20s cho cac replica set bau primary..."
Start-Sleep -Seconds 20
Write-Host "==> NHO: khoi dong mongos tren PC4 (deploy\pc4-master\start_mongos.ps1) truoc buoc 4!"

Write-Host "==> 4. Them shard + bat sharding cho DB 'social'"
mongosh --host $env:PC4_IP --port 27017 --eval @"
sh.addShard('rs1/$($env:PC2_IP):27018');
sh.addShard('rs2/$($env:PC3_IP):27018');
sh.enableSharding('social');
sh.shardCollection('social.posts',    { author_id: 'hashed' });
sh.shardCollection('social.comments', { post_id: 'hashed' });
sh.shardCollection('social.users',    { _id: 'hashed' });
sh.status();
"@
Write-Host "==> HOAN TAT. Kiem tra: mongosh --host $($env:PC4_IP) --eval 'sh.status()'"
