# Giả lập PC4: tải Neo4j Community vào .local-4pc\neo4j và cấu hình (chỉ cần chạy 1 lần).
$ErrorActionPreference = "Stop"
$version = "2026.09.0"
$root = Resolve-Path "$PSScriptRoot\..\.."
$data = Join-Path $root ".local-4pc"
$home4j = Join-Path $data "neo4j"
$zipName = "neo4j-community-$version-windows.zip"
$url = "https://dist.neo4j.org/$zipName"

$env:JAVA_HOME = (Get-ChildItem "$env:USERPROFILE\.Neo4jDesktop2\Cache\runtime" -Directory -Filter "zulu21*" | Select-Object -First 1).FullName
if (-not $env:JAVA_HOME) { throw "Khong tim thay Java 21 (Neo4j Desktop runtime)" }

if (Test-Path $home4j) { Write-Host "==> Da co $home4j, bo qua"; exit 0 }

$tmp = Join-Path $env:TEMP "neo4j-download-$version"
New-Item -ItemType Directory -Force -Path $tmp, $data | Out-Null
$zip = Join-Path $tmp $zipName

Write-Host "==> Tai $url ..."
curl.exe -fsSL -o $zip $url
if ($LASTEXITCODE) { throw "Tai that bai" }
$expected = (curl.exe -fsSL "$url.sha256").Trim().Split(" ")[0]
$actual = (Get-FileHash $zip -Algorithm SHA256).Hash
if ($actual -ne $expected) { throw "Sai SHA-256: $actual <> $expected" }
Write-Host "==> SHA-256 khop"

tar.exe -xf $zip -C $data
if ($LASTEXITCODE) { throw "Giai nen that bai" }
Rename-Item (Join-Path $data "neo4j-community-$version") "neo4j"
Remove-Item $tmp -Recurse -Force

# PC4 = 127.0.1.4, gioi han RAM vi chay chung 1 may voi cac nut MongoDB
Add-Content (Join-Path $home4j "conf\neo4j.conf") -Encoding ascii @"

server.default_listen_address=127.0.1.4
server.memory.heap.initial_size=512m
server.memory.heap.max_size=512m
server.memory.pagecache.size=256m
server.jvm.additional=-Djdk.net.unixdomain.tmpdir=$($env:USERPROFILE -replace '\\', '/')/.minisocial-sock
"@
# AF_UNIX connect bi loi 10022 trong thu muc Temp tren may nay, nen socket noi bo cua Java dat o ngoai Temp
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.minisocial-sock" | Out-Null

$password = (Get-Content (Join-Path $root ".env") | Where-Object { $_ -match '^NEO4J_PASSWORD=' }) -replace '^NEO4J_PASSWORD=', ''
& (Join-Path $home4j "bin\neo4j-admin.bat") dbms set-initial-password $password
if ($LASTEXITCODE) { throw "Khong dat duoc mat khau Neo4j" }
Write-Host "==> Neo4j san sang tai $home4j"
