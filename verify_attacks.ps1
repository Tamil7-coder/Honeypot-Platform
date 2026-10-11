<#
.SYNOPSIS
    Honeypot pipeline verification: fires a benign test payload at each of
    the platform's 5 emulated protocols (SSH/Telnet via Cowrie, HTTP/FTP/SMB
    via Dionaea), waits for the shippers to flush, then queries the backend
    API to confirm every protocol was ingested end-to-end.

.DESCRIPTION
    This script does NOT test for real vulnerabilities. It sends the minimum
    protocol handshake/payload needed for each honeypot to log a session
    (e.g. an FTP USER/PASS sequence, an HTTP GET), purely to exercise the
    log -> shipper -> backend ingestion pipeline end-to-end.

.PARAMETER BaseUrl
    Base URL of the backend API. Defaults to http://localhost:8000.

.PARAMETER AdminEmail / AdminPassword
    Credentials for a platform user, used to obtain a JWT so the
    authenticated GET /api/v1/attacks endpoint can be queried. Defaults to
    the seeded default admin from .env.example.

.EXAMPLE
    .\verify_attacks.ps1
    .\verify_attacks.ps1 -BaseUrl "http://localhost:8000" -WaitSeconds 15
#>

param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$AdminEmail = "admin@honeypot-platform.com",
    [string]$AdminPassword = "ChangeMe123!",
    [int]$WaitSeconds = 10,
    [string]$TargetHost = "localhost"
)

$ErrorActionPreference = "Continue"
$ApiPrefix = "$BaseUrl/api/v1"

function Write-Section($text) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host " $text" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
}

function Send-TcpPayload {
    param(
        [string]$TargetHost,
        [int]$Port,
        [byte[]]$Bytes,
        [int]$ReadTimeoutMs = 1500,
        [switch]$ReadResponse
    )
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $connectTask = $client.ConnectAsync($TargetHost, $Port)
        if (-not $connectTask.Wait(3000)) {
            Write-Host "  [FAIL] Could not connect to $($TargetHost):$Port (timeout)" -ForegroundColor Red
            return $false
        }
        $stream = $client.GetStream()
        if ($Bytes -and $Bytes.Length -gt 0) {
            $stream.Write($Bytes, 0, $Bytes.Length)
            $stream.Flush()
        }
        if ($ReadResponse) {
            $stream.ReadTimeout = $ReadTimeoutMs
            $buffer = New-Object byte[] 512
            try { [void]$stream.Read($buffer, 0, $buffer.Length) } catch { }
        } else {
            Start-Sleep -Milliseconds 300
        }
        $client.Close()
        Write-Host "  [OK] Payload sent to $($TargetHost):$Port" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "  [FAIL] $($TargetHost):$Port -> $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# ---------------------------------------------------------------------------
# 1. Fire test payloads at all 5 protocols
# ---------------------------------------------------------------------------
Write-Section "Sending Test Payloads to All 5 Honeypot Protocols"

# --- SSH (Cowrie, port 2222) ---
# A raw SSH client handshake is heavyweight to reimplement; sending the
# client's initial version-exchange banner is enough for Cowrie to open and
# log a session before it drops the malformed follow-on handshake.
Write-Host "[1/5] SSH (port 2222)..."
Send-TcpPayload -TargetHost $TargetHost -Port 2222 -Bytes ([System.Text.Encoding]::ASCII.GetBytes("SSH-2.0-VerifyAttacksScript`r`n")) | Out-Null

# --- Telnet (Cowrie, port 2223) ---
Write-Host "[2/5] Telnet (port 2223)..."
$telnetPayload = [System.Text.Encoding]::ASCII.GetBytes("root`r`ntoor`r`n")
Send-TcpPayload -TargetHost $TargetHost -Port 2223 -Bytes $telnetPayload | Out-Null

# --- HTTP (Dionaea, port 8080) ---
Write-Host "[3/5] HTTP GET /admin/login.php (port 8080)..."
try {
    Invoke-WebRequest -Uri "http://$($TargetHost):8080/admin/login.php" -UseBasicParsing -TimeoutSec 5 | Out-Null
    Write-Host "  [OK] HTTP request sent" -ForegroundColor Green
} catch {
    # Dionaea's emulated httpd commonly returns a non-200 or resets the
    # connection after logging the request -- that's expected, not a failure.
    Write-Host "  [OK] HTTP request sent (server responded/closed: $($_.Exception.Message))" -ForegroundColor Green
}

# --- FTP (Dionaea, port 2121) ---
Write-Host "[4/5] FTP USER/PASS sequence (port 2121)..."
$ftpPayload = [System.Text.Encoding]::ASCII.GetBytes("USER admin`r`nPASS admin123`r`nQUIT`r`n")
Send-TcpPayload -TargetHost $TargetHost -Port 2121 -Bytes $ftpPayload -ReadResponse | Out-Null

# --- SMB (Dionaea, port 4450) ---
# A minimal SMB negotiate-protocol request header (NetBIOS session +
# SMB header with the negotiate command) is enough to trigger a logged
# connection/incident on Dionaea's smbd handler.
Write-Host "[5/5] SMB TCP handshake (port 4450)..."
$smbBytes = [byte[]](
    0x00,0x00,0x00,0x2f,                                     # NetBIOS session header, length
    0xff,0x53,0x4d,0x42,0x72,                                # \xffSMBr (negotiate protocol)
    0x00,0x00,0x00,0x00,0x00,0x18,0x53,0xc8,
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00,0xff,0xfe,0x00,0x00,
    0x00,0x00,0x00,0x0c,0x00,0x02,0x4e,0x54,
    0x20,0x4c,0x4d,0x20,0x30,0x2e,0x31,0x32,0x00
)
Send-TcpPayload -TargetHost $TargetHost -Port 4450 -Bytes $smbBytes -ReadResponse | Out-Null

# ---------------------------------------------------------------------------
# 2. Wait for shippers to flush sessions to the backend
# ---------------------------------------------------------------------------
Write-Section "Waiting $WaitSeconds seconds for log shippers to flush sessions..."
Start-Sleep -Seconds $WaitSeconds

# ---------------------------------------------------------------------------
# 3. Authenticate against the backend API
# ---------------------------------------------------------------------------
Write-Section "Authenticating with Backend API"

$token = $null
try {
    $loginBody = @{ email = $AdminEmail; password = $AdminPassword } | ConvertTo-Json
    $loginResp = Invoke-RestMethod -Uri "$ApiPrefix/auth/login" -Method Post -Body $loginBody -ContentType "application/json" -TimeoutSec 10
    $token = $loginResp.access_token
    if ($token) {
        Write-Host "[OK] Authenticated as $AdminEmail" -ForegroundColor Green
    }
} catch {
    Write-Host "[ERROR] Login failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "        Check -AdminEmail / -AdminPassword, or that the backend is up." -ForegroundColor Yellow
}

if (-not $token) {
    Write-Host ""
    Write-Host "Cannot verify ingestion without a valid API token. Exiting." -ForegroundColor Red
    exit 1
}

$headers = @{ Authorization = "Bearer $token" }

# ---------------------------------------------------------------------------
# 4. Query the backend per protocol and build the status report
# ---------------------------------------------------------------------------
Write-Section "Verifying Ingested Attack Sessions per Protocol"

$protocols = @(
    @{ Name = "SSH";    Filter = "ssh" },
    @{ Name = "Telnet"; Filter = "telnet" },
    @{ Name = "HTTP";   Filter = "http" },
    @{ Name = "FTP";    Filter = "ftp" },
    @{ Name = "SMB";    Filter = "smb" }
)

$results = @()
foreach ($p in $protocols) {
    try {
        $uri = "$ApiPrefix/attacks?protocol=$($p.Filter)&limit=5"
        $resp = Invoke-RestMethod -Uri $uri -Headers $headers -Method Get -TimeoutSec 10
        $count = if ($resp.total) { $resp.total } elseif ($resp.items) { $resp.items.Count } else { 0 }
        $results += [PSCustomObject]@{
            Protocol = $p.Name
            Sessions = $count
            Status   = if ($count -gt 0) { "PASS" } else { "FAIL" }
        }
    } catch {
        $results += [PSCustomObject]@{
            Protocol = $p.Name
            Sessions = 0
            Status   = "ERROR"
        }
    }
}

Write-Host ""
$results | Format-Table -AutoSize | Out-String | Write-Host

$passed = ($results | Where-Object { $_.Status -eq "PASS" }).Count
$total = $results.Count

Write-Section "Summary"
foreach ($r in $results) {
    $color = if ($r.Status -eq "PASS") { "Green" } elseif ($r.Status -eq "FAIL") { "Red" } else { "Yellow" }
    Write-Host ("  {0,-8} : {1}" -f $r.Protocol, $r.Status) -ForegroundColor $color
}
Write-Host ""

if ($passed -eq $total) {
    Write-Host "ALL $total/$total PROTOCOLS VERIFIED - pipeline is healthy." -ForegroundColor Green
    exit 0
} else {
    Write-Host "$passed/$total protocols verified. Investigate the failing shipper(s):" -ForegroundColor Yellow
    Write-Host "  docker compose logs cowrie-shipper" -ForegroundColor Yellow
    Write-Host "  docker compose logs dionaea-shipper" -ForegroundColor Yellow
    Write-Host "  docker compose logs dionaea" -ForegroundColor Yellow
    exit 1
}
