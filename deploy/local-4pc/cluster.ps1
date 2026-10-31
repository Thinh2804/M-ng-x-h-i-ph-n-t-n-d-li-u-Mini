# Giả lập 4 máy trên 1 máy: mỗi PC là 1 địa chỉ loopback riêng, cổng giữ nguyên như README.
#   powershell -ExecutionPolicy Bypass -File deploy\local-4pc\cluster.ps1 start|stop|status
#   ... cluster.ps1 stop-node pc2-rs1      (tắt 1 nút để thử chịu lỗi)
param(
    [ValidateSet("start", "stop", "status", "stop-node", "start-node")][string]$Action = "status",
    [string]$Node
)
$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\..\.."
$data = Join-Path $root ".local-4pc"
$python = Join-Path $root "backend-python\.venv\Scripts\python.exe"
$mongoBin = (Get-ChildItem "C:\Program Files\MongoDB\Server" -Directory | Sort-Object Name | Select-Object -Last 1).FullName + "\bin"
$env:PYTHONIOENCODING = "utf-8"

$nodes = @(
    @{ name = "pc1-cfg";    ip = "127.0.1.1"; port = 27019; args = "--configsvr --replSet cfgrs" }
    @{ name = "pc2-cfg";    ip = "127.0.1.2"; port = 27019; args = "--configsvr --replSet cfgrs" }
    @{ name = "pc3-cfg";    ip = "127.0.1.3"; port = 27019; args = "--configsvr --replSet cfgrs" }
    @{ name = "pc2-rs1";    ip = "127.0.1.2"; port = 27018; args = "--shardsvr --replSet rs1" }
    @{ name = "pc2-rs2sec"; ip = "127.0.1.2"; port = 27029; args = "--shardsvr --replSet rs2" }
    @{ name = "pc3-rs2";    ip = "127.0.1.3"; port = 27018; args = "--shardsvr --replSet rs2" }
    @{ name = "pc3-rs1sec"; ip = "127.0.1.3"; port = 27028; args = "--shardsvr --replSet rs1" }
    @{ name = "pc4-rs1sec"; ip = "127.0.1.4"; port = 27038; args = "--shardsvr --replSet rs1" }
    @{ name = "pc4-rs2sec"; ip = "127.0.1.4"; port = 27039; args = "--shardsvr --replSet rs2" }
)

function Test-Port($ip, $port) {
    $c = New-Object Net.Sockets.TcpClient
    try { $c.Connect($ip, $port); return $true } catch { return $false } finally { $c.Close() }
}

function Start-MongodNode($n) {
    if (Test-Port $n.ip $n.port) { return }
    $db = Join-Path $data "db\$($n.name)"
    New-Item -ItemType Directory -Force -Path $db, "$data\log" | Out-Null
    Start-Process "$mongoBin\mongod.exe" -WindowStyle Hidden -ArgumentList (
        "$($n.args) --port $($n.port) --bind_ip $($n.ip) --dbpath `"$db`" " +
        "--logpath `"$data\log\$($n.name).log`" --logappend --wiredTigerCacheSizeGB 0.25")
}

# Chuyển hướng log bằng cmd: Start-Process -RedirectStandardOutput làm tiến trình con giữ stdout của script
function Start-Neo4j {
    if (Test-Port "127.0.1.4" 7687) { return }
    New-Item -ItemType Directory -Force -Path "$data\log", "$env:USERPROFILE\.minisocial-sock" | Out-Null
    $env:JAVA_HOME = (Get-ChildItem "$env:USERPROFILE\.Neo4jDesktop2\Cache\runtime" -Directory -Filter "zulu21*" | Select-Object -First 1).FullName
    Start-Process cmd.exe -WindowStyle Hidden -ArgumentList (
        "/c `"`"$data\neo4j\bin\neo4j.bat`" console > `"$data\log\pc4-neo4j.log`" 2>&1`"")
}

function Wait-Port($ip, $port, $seconds = 60) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Port $ip $port) { return }
        Start-Sleep -Seconds 1
    }
    throw "Het thoi gian cho ${ip}:$port"
}

# Chỉ dừng tiến trình chạy từ .local-4pc - không đụng service MongoDB của Windows
function Stop-Matching($pattern) {
    Get-CimInstance Win32_Process |
        Where-Object { $_.Name -match '^(mongod|mongos|java)\.exe$' -and $_.CommandLine -and $_.CommandLine.Contains($pattern) } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
}

switch ($Action) {
    "start" {
        Write-Host "==> PC1-PC4: khoi dong 3 config server va 6 nut shard..."
        foreach ($n in $nodes) { Start-MongodNode $n }
        foreach ($n in $nodes) { Wait-Port $n.ip $n.port }

        & $python (Join-Path $root "scripts\init_cluster_local.py") replicasets
        if ($LASTEXITCODE) { throw "Khoi tao replica set that bai" }

        Write-Host "==> PC4: khoi dong mongos (127.0.1.4:27017)..."
        if (-not (Test-Port "127.0.1.4" 27017)) {
            New-Item -ItemType Directory -Force -Path "$data\log" | Out-Null
            Start-Process "$mongoBin\mongos.exe" -WindowStyle Hidden -ArgumentList (
                "--configdb cfgrs/127.0.1.1:27019,127.0.1.2:27019,127.0.1.3:27019 --port 27017 --bind_ip 127.0.1.4 " +
                "--logpath `"$data\log\pc4-mongos.log`" --logappend")
        }
        Wait-Port "127.0.1.4" 27017

        & $python (Join-Path $root "scripts\init_cluster_local.py") shards
        if ($LASTEXITCODE) { throw "Them shard that bai" }

        Write-Host "==> PC4: khoi dong Neo4j (127.0.1.4:7687)..."
        Start-Neo4j
        Wait-Port "127.0.1.4" 7687 120
        Write-Host "==> Cum da san sang."
    }
    "stop" {
        & $python (Join-Path $root "scripts\init_cluster_local.py") shutdown
        Stop-Matching ".local-4pc"
        Stop-Matching "cfgrs/127.0.1.1:27019"
        Write-Host "==> Da dung cum (service MongoDB cua Windows khong bi anh huong)."
    }
    "stop-node" {
        if ($Node -eq "pc4-neo4j") { Stop-Matching ".local-4pc\neo4j" } else { Stop-Matching "db\$Node" }
        Write-Host "==> Da tat nut $Node"
    }
    "start-node" {
        if ($Node -eq "pc4-neo4j") { Start-Neo4j; Wait-Port "127.0.1.4" 7687 120 }
        else { Start-MongodNode ($nodes | Where-Object { $_.name -eq $Node }) }
        Write-Host "==> Da bat nut $Node"
    }
    "status" {
        foreach ($n in $nodes) {
            "{0,-12} {1,-18} {2}" -f $n.name, "$($n.ip):$($n.port)", $(if (Test-Port $n.ip $n.port) { "UP" } else { "DOWN" })
        }
        "{0,-12} {1,-18} {2}" -f "pc4-mongos", "127.0.1.4:27017", $(if (Test-Port "127.0.1.4" 27017) { "UP" } else { "DOWN" })
        "{0,-12} {1,-18} {2}" -f "pc4-neo4j", "127.0.1.4:7687", $(if (Test-Port "127.0.1.4" 7687) { "UP" } else { "DOWN" })
    }
}
