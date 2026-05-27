# Yes-Engineer

Claude Code CLI + BLE Buddy 硬件审批系统。

## 架构

```
Claude Code CLI
  └─ PermissionRequest hook (hook.py)
       └─ TCP (127.0.0.1:19876)
            └─ cdbb daemon (bridge.py)
                 └─ BLE (Nordic UART Service)
                      └─ M5StickC Plus (Claude-21D1)
```

## 安装

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

## 启动守护进程

```powershell
powershell -File cdbb-start.ps1
```

## 组件

| 文件 | 说明 |
|------|------|
| `cdbb/__init__.py` | 包元数据 |
| `cdbb/bridge.py` | BLE 桥接守护进程 (TCP 服务器 + NUS 通信) |
| `cdbb/hook.py` | Claude Code PermissionRequest hook (TCP 客户端) |
| `cdbb/cli.py` | 命令行入口 (daemon/scan/status/install/uninstall) |
| `setup.ps1` | 一键安装脚本 |
| `cdbb-start.ps1` | 一键启动守护进程 |

## 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `CDBB_DEVICE_ID` | Windows 蓝牙设备 ID | `BluetoothLE#BluetoothLE14:...` |
| `CDBB_ADDR` | 设备 MAC 地址 | `70:04:1D:D6:21:D1` |

## 注意事项

- Windows 需要在蓝牙设置中配对设备（ProtectionLevel 1 = Encryption），否则 NUS 服务会被锁定
- 守护进程退出后 PermissionRequest hook 会 fail-open，不影响正常使用
