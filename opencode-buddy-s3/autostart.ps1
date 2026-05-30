# Opencode-Buddy-S3 开机自动启动注册脚本
# 原理：将启动命令放入 Windows Startup 文件夹

$scriptPath = "C:\Users\home\opencode-buddy-s3\bridge\bridge.py"
$startupFolder = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupFolder "OpencodeBuddy.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = "python"
$Shortcut.Arguments = "$scriptPath"
$Shortcut.WorkingDirectory = "C:\Users\home\opencode-buddy-s3\bridge"
$Shortcut.WindowStyle = 7 # 最小化运行
$Shortcut.Save()

Write-Host "已注册开机自启。"
