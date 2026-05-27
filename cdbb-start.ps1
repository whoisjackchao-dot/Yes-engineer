# cdbb-start.ps1 — 一键启动 cdbb 守护进程
# 使用前请修改下方的设备ID和MAC地址

$env:CDBB_DEVICE_ID = 'BluetoothLE#BluetoothLE14:4f:8a:7a:bb:b4-70:04:1d:d6:21:d1'
$env:CDBB_ADDR       = '70:04:1D:D6:21:D1'

Write-Host "cdbb daemon starting..." -ForegroundColor Cyan
$proc = Start-Process python -ArgumentList '-c', 'import cdbb.cli; cdbb.cli.main()', 'daemon', '-v' -NoNewWindow -PassThru
Write-Host "PID: $($proc.Id)"

Start-Sleep -Seconds 12
try {
    $c = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 19876)
    $c.Close()
    Write-Host "cdbb daemon: RUNNING (TCP 127.0.0.1:19876)" -ForegroundColor Green
} catch {
    Write-Host "cdbb daemon: FAILED — check BLE device is powered on" -ForegroundColor Red
}
