# cdbb-daemon-launcher.ps1 — 守护进程启动器（含存活检查）
# 用于计划任务和 SessionStart hook，避免重复启动

$ErrorActionPreference = "Stop"

$env:CDBB_DEVICE_ID = "BluetoothLE#BluetoothLE14:4f:8a:7a:bb:b4-70:04:1d:d6:21:d1"
$env:CDBB_ADDR       = "70:04:1D:D6:21:D1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8       = "1"

$logDir  = "$env:USERPROFILE\.claude\logs"
$logFile = Join-Path $logDir "cdbb-daemon.log"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts  $msg" | Out-File -Append -Encoding utf8 $logFile
}

try {
    $c = New-Object System.Net.Sockets.TcpClient("127.0.0.1", 19876)
    $c.Close()
    Write-Log "Daemon already running, nothing to do."
    exit 0
}
catch {
    Write-Log "Daemon not running, starting..."
}

try {
    $proc = Start-Process python -ArgumentList "-c", "import cdbb.cli; cdbb.cli.main()", "daemon", "-v" -WindowStyle Hidden -PassThru

    Start-Sleep -Seconds 15

    try {
        $c = New-Object System.Net.Sockets.TcpClient("127.0.0.1", 19876)
        $c.Close()
        Write-Log "Daemon started successfully (PID: $($proc.Id))"
    }
    catch {
        Write-Log "Daemon may have failed to start (PID: $($proc.Id)), check BLE device"
    }
}
catch {
    Write-Log "ERROR: Failed to start daemon process: $_"
    exit 1
}
