# setup.ps1 — 安装 cdbb (claude-desktop-buddy-bridge)
# 用法: powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== cdbb 安装 ===" -ForegroundColor Cyan

# 1. 安装 Python 依赖
Write-Host "[1/3] Installing Python dependencies..."
python -m pip install bleak -q

# 2. 复制 cdbb 包到 site-packages
Write-Host "[2/3] Installing cdbb package..."
$sitePackages = python -c "import site; print(site.getsitepackages()[0])"
$dest = Join-Path $sitePackages "cdbb"
if (-not (Test-Path $dest)) { New-Item -ItemType Directory $dest -Force | Out-Null }
Get-ChildItem "$PSScriptRoot\cdbb\*.py" | ForEach-Object {
    Copy-Item $_.FullName $dest -Force
}
Write-Host "  -> $dest"

# 3. 注入 Claude Code hook 配置
Write-Host "[3/3] Installing PermissionRequest hook..."
python -c "import cdbb.cli; cdbb.cli.main()" install --force
Write-Host "  -> Hook configured"

Write-Host ""
Write-Host "=== 安装完成 ===" -ForegroundColor Green
Write-Host ""
Write-Host "启动守护进程:"
Write-Host "  CDBB_DEVICE_ID=<your-device-id> CDBB_ADDR=<mac> python -c 'import cdbb.cli; cdbb.cli.main()' daemon -v"
Write-Host ""
Write-Host "或运行:"
Write-Host "  powershell -File $PSScriptRoot\cdbb-start.ps1"
