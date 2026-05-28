"""
将 Yes-engineer 项目完整技术文档写入 ClickUp。

用法: python write_docs.py
需要环境变量 CLICKUP_API_TOKEN
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

API_TOKEN = os.environ.get("CLICKUP_API_TOKEN", "")
WORKSPACE_ID = "90182731581"
DOC_ID = "2kzmyhtx-878"
API_BASE = f"https://api.clickup.com/api/v3/workspaces/{WORKSPACE_ID}"


def api(path: str, method: str = "GET", body: dict | None = None) -> Any:
    url = f"{API_BASE}{path}"
    headers = {"Authorization": API_TOKEN, "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode() if e.fp else ""
        print(f"  HTTP {e.code}: {err}", file=sys.stderr)
        return {"error": f"HTTP {e.code}"}


def main():
    if not API_TOKEN:
        print("错误: 请设置 CLICKUP_API_TOKEN 环境变量", file=sys.stderr)
        sys.exit(1)

    # ── 1. 获取现有页面 ──────────────────────────────────────
    print("获取现有页面...")
    existing = api(f"/docs/{DOC_ID}/pages")
    if isinstance(existing, dict) and "value" in existing:
        existing_pages = existing["value"]
    elif isinstance(existing, list):
        existing_pages = existing
    else:
        existing_pages = []

    existing_by_index = {}
    for p in existing_pages:
        idx = p.get("order_index", 99)
        existing_by_index[idx] = p

    print(f"  现有 {len(existing_pages)} 个页面")

    # ── 2. 定义页面内容 ──────────────────────────────────────

    pages = [
        {
            "name": "cdbb 技术架构总览",
            "content": """# cdbb (claude-desktop-buddy-bridge) v0.1.0

Claude Code CLI 与 BLE Buddy 硬件审批按钮之间的桥接系统。当 Claude Code 需要执行需要用户授权的工具调用时，通过 PermissionRequest hook 将请求发送到守护进程，守护进程通过 BLE 将请求推送到 M5StickC Plus 设备上，用户通过设备上的物理按钮一键批准或拒绝。

## 架构

```
Claude Code CLI
  └─ PermissionRequest hook (hook.py)
       └─ TCP 127.0.0.1:19876 (Windows) / Unix Socket /tmp/cdbb.sock (Linux/Mac)
            └─ cdbb daemon (bridge.py)
                 └─ BLE Nordic UART Service (NUS)
                      └─ M5StickC Plus (ESP32, BLE name: Claude-21D1)
```

## 核心流程

1. Claude Code 在每次工具调用前触发 PermissionRequest hook
2. Hook 通过 TCP/Unix Socket 向守护进程发送请求 JSON `{id, tool, hint}`
3. 守护进程通过 BLE NUS 推送到 M5StickC Plus 屏幕显示
4. 用户在设备上按键决策（一次性允许 / 拒绝）
5. 设备通过 BLE Notify 返回决策 `{cmd: "permission", id, decision}`
6. 守护进程将 decision 写回 hook 进程
7. Hook 输出 Claude Code 协议 JSON，allow 则继续，deny 则终止

## 关键设计原则

| 原则 | 说明 |
|------|------|
| Fail-open | 守护进程不在线时 hook 退出 0 无输出，CC 自己弹权限对话框，不阻塞任何操作 |
| 请求串行化 | `permission_lock` 确保同时只有一个请求在处理，第二个请求在前一个完成后才弹出 |
| EOF 竞争检测 | 如果 hook 进程提前退出（用户 Esc / CC 超时），立即清空设备显示，不傻等超时 |
| 心跳保活 | 每 3 秒推送一次快照，连续 5 次失败后 `os._exit(1)`，由 supervisor 重启 |
| 中文 sanitize | 非 ASCII 字符转为 `?` 再发送，避免固件 5×7 点阵字体索引越界导致蓝牙栈重置 |

## 组件清单

| 文件 | 说明 |
|------|------|
| `cdbb/__init__.py` | 包元数据，版本号 |
| `cdbb/bridge.py` | BLE 桥接守护进程核心：NUS 通信、TCP/Unix Socket 服务器、并发管理 |
| `cdbb/hook.py` | Claude Code PermissionRequest hook：TCP 客户端、CC 协议翻译 |
| `cdbb/cli.py` | 命令行入口：daemon、scan、status、install、uninstall |
| `setup.ps1` | 一键安装脚本 |
| `cdbb-start.ps1` | 一键启动守护进程脚本 |
| `cdbb-autostart.ps1` | 开机自动启动注册脚本 |
| `cdbb-daemon-launcher.ps1` | 守护进程启动器（含存活检查） |
""",
        },
        {
            "name": "BLE 通信与配对 (Windows)",
            "content": r"""# BLE 通信与配对 (Windows)

## Nordic UART Service (NUS)

M5StickC Plus 使用标准 NUS UUID：

| 角色 | UUID | 说明 |
|------|------|------|
| NUS Service | `6e400001-b5a3-f393-e0a9-e50e24dcca9e` | - |
| RX Characteristic | `6e400002-b5a3-f393-e0a9-e50e24dcca9e` | 主机 → 设备 (Write) |
| TX Characteristic | `6e400003-b5a3-f393-e0a9-e50e24dcca9e` | 设备 → 主机 (Notify) |

## BLE 设备发现

设备以广播名 `Claude-21D1` 出现。守护进程支持两种发现方式：

1. **自动扫描**：通过 `BleakScanner.find_device_by_filter` 扫描以 `Claude` 开头的设备
2. **环境变量直接指定**：设置 `CDBB_ADDR=70:04:1D:D6:21:D1` 跳过扫描，加速启动

## Windows 配对问题（关键）

### 问题背景

- bleak WinRT 后端使用 `FromBluetoothAddressAsync()` 连接设备
- 已配对但不广播的设备无法通过此方法找到（返回 null）
- **解决方案**：使用 `FromIdAsync()` 通过 Windows 蓝牙设备 ID 连接

### 设备 ID 格式

```
BluetoothLE#BluetoothLE14:4f:8a:7a:bb:b4-70:04:1d:d6:21:d1
```

通过环境变量 `CDBB_DEVICE_ID` 传入。

### 配对保护级别 (ProtectionLevel)

| Level | 值 | 说明 |
|-------|-----|------|
| NONE | 0 | 无保护 |
| ENCRYPTION | 1 | 加密 → NUS 可正常访问 |
| ENCRYPTION_AND_AUTHENTICATION | 2 | 加密+认证 → NUS 被锁定 (ACCESS_DENIED) |
| ENCRYPTION_AND_AUTHENTICATION_WITH_BONDING | 3 | 加密+认证+绑定 |

**Windows 蓝牙设置 UI 默认使用 Level 2/3**，会导致 NUS 服务被锁定，`start_notify` 失败（Insufficient Authentication, protocol error 5）。

### 配对修复 (`_patched_pair`)

```
1. 通过 DeviceInformation.CreateFromIdAsync 获取设备信息
2. 如果已配对 → 先解除配对 (unpair_async)
3. 等待 2 秒
4. 重新获取设备信息
5. 如果 can_pair == false → 跳过配对（Windows 已自动管理）
6. 分级尝试配对：
   a. ENCRYPTION (level=1) → 首选
   b. NONE (level=0) → 回退
7. 如果都未成功 → 使用默认 pair_async 方案
```

### 配对结果状态码

| 状态 | 值 | 说明 |
|------|-----|------|
| PAIRED | 0 | 成功 |
| PROTECTION_LEVEL_COULD_NOT_BE_MET | 19 | 级别不可达，尝试更低级别 |

## BLE 消息协议

### 主机 → 设备 (Write)

JSON 行格式（`ensure_ascii=True`，避免 GBK 编码问题）：

```json
{"total":1,"running":0,"waiting":1,"msg":"approve: Bash","entries":["23:08 git status"],"tokens":0,"tokens_today":0,"prompt":{"id":"req_1717000000000","tool":"Bash","hint":"git status"}}
```

### 设备 → 主机 (Notify)

```json
{"cmd":"permission","id":"req_1717000000000","decision":"once"}
```

### 其他消息

- **时钟同步**：`{"time": [<epoch_seconds>, <tz_offset_seconds>]}`
- **Ack**：`{"ack": "permission", "ok": true, "n": 0}`

## 心跳机制

- 每 3 秒推送一次快照，与官方桌面端保持一致
- 连续 5 次写入失败 → `os._exit(1)`，绕过 asyncio 清理避免 BleakClient 死锁
- 由 supervisor（systemd/launchd/手动启动）自动重启
""",
        },
        {
            "name": "Socket 通信协议",
            "content": """# Socket 通信协议

## 平台差异

| 平台 | 传输方式 | 地址 |
|------|----------|------|
| Windows | TCP | `127.0.0.1:19876` |
| Linux | Unix Domain Socket | `/tmp/cdbb.sock` |
| macOS | Unix Domain Socket | `/tmp/cdbb.sock` |

```python
# bridge.py / hook.py 中的选择逻辑
if sys.platform == "win32":
    SOCKET_HOST = "127.0.0.1"
    SOCKET_PORT = 19876
    SOCKET_PATH = None  # Windows 使用 TCP
else:
    SOCKET_HOST = None
    SOCKET_PORT = None
    SOCKET_PATH = "/tmp/cdbb.sock"
```

## TCP 服务器 (bridge.py)

```python
server = await asyncio.start_server(
    bridge.handle_hook_client,
    host="127.0.0.1", port=19876,
)
```

绑定 `127.0.0.1` 而非 `0.0.0.0`，只允许本机访问。

## Unix Socket 服务器 (bridge.py)

```python
server = await asyncio.start_unix_server(
    bridge.handle_hook_client, path="/tmp/cdbb.sock"
)
os.chmod(SOCKET_PATH, 0o600)  # 仅 owner 可读写
```

## 请求/响应协议

### 请求（Hook → Daemon）

一行 JSON，以 `\\n` 结尾：

```json
{"id":"hook_abc123","tool":"Bash","hint":"git status"}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | tool_use_id，用于匹配决策 |
| tool | string | 工具名称 (Bash, Write, Edit, Read...) |
| hint | string | 操作摘要，从 tool_input 提取 |

### 响应（Daemon → Hook）

一行 JSON，以 `\\n` 结尾：

```json
{"decision":"once"}
```

| decision | 含义 | Hook 行为 |
|----------|------|-----------|
| `"once"` | 允许本次 | `_emit_allow()` 输出 `behavior: "allow"` |
| `"deny"` | 拒绝 | `_emit_deny()` 输出 `behavior: "deny"` |
| `"timeout"` | 超时 (110s) | `_fail_open()` 让 CC 自己处理 |
| `"abandoned"` | Hook 进程提前退出 | `_fail_open()` 让 CC 自己处理 |

## 超时配置

| 超时 | 值 | 说明 |
|------|-----|------|
| 连接超时 | 1.0s | Hook 连接 daemon 的 TCP 超时 |
| 请求读取超时 | 5.0s | Daemon 等待 hook 发送请求行 |
| 审批超时 | 110.0s | 必须小于 CC hook 总超时 (120s) |
| Hook 读取超时 | 115.0s | Hook 等待 daemon 返回决策 |
| BLE 连接超时 | 30.0s | BleakClient 连接超时 |

## EOF 竞争处理

当 hook 进程等待决策时：

```python
asyncio.wait([decision_task, eof_task], FIRST_COMPLETED)
```

- `decision_task` 胜出 → 取消 eof_task，返回 decision 给 hook
- `eof_task` 胜出 → hook 进程提前退出（用户按 Esc / CC 超时），立即清空设备显示，decision 设为 "abandoned"

避免 hook 被 kill 后设备一直亮着等待用户操作。
""",
        },
        {
            "name": "Hook 协议与 CC 集成",
            "content": """# Hook 协议与 Claude Code 集成

## PermissionRequest Hook 机制

Claude Code 在每次需要用户授权工具调用时触发 PermissionRequest hook。

**注意**：Hook 仅在权限对话框需要弹出时才会触发。如果操作已经被预先授权（如 continued session 中的批准工具），hook 不会被触发。

## Hook 配置 (settings.json)

```json
{
  "hooks": {
    "PermissionRequest": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "C:\\\\Python314\\\\python.exe C:\\\\Users\\\\home\\\\AppData\\\\Roaming\\\\Python\\\\Python314\\\\site-packages\\\\cdbb\\\\hook.py",
            "timeout": 120
          }
        ]
      }
    ]
  }
}
```

可通过 `cdbb install` 自动注入，`cdbb uninstall` 移除。

## Hook 输入 (stdin JSON)

Claude Code 通过 stdin 传入 hook：

```json
{
  "session_id": "abc123",
  "tool_name": "Bash",
  "tool_input": {
    "command": "git status"
  },
  "tool_use_id": "toolu_01ABCDEF"
}
```

## Hook 输出 (stdout JSON)

### 允许操作

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": {"behavior": "allow"}
  }
}
```

### 拒绝操作

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": {
      "behavior": "deny",
      "message": "已通过 cdbb 拒绝此操作"
    }
  }
}
```

### 透传（Fail-open）

不输出任何 JSON，exit(0)，Claude Code 显示自己的权限对话框。

## Hint 提取逻辑

Hook 从 `tool_input` 中按优先级提取操作摘要：

```python
_HINT_KEYS = ("command", "file_path", "url", "path", "pattern", "query", "prompt", "input")
```

取第一个非空字符串，最长 200 字符。这决定了设备屏幕上显示什么内容。

## 手动测试

可通过管道直接测试 hook：

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"ls"},"tool_use_id":"test1"}' | python hook.py
```

预期：
- 守护进程在线 → stdout 输出 allow/deny JSON
- 守护进程不在线 → stdout 无内容，exit(0)

## 常见排查

| 问题 | 可能原因 | 检查方法 |
|------|----------|----------|
| Hook 未触发 | 操作已被预授权 | 新开会话测试 |
| Hook 连接失败 | 守护进程未运行 | `cdbb status` |
| Unicode 乱码 | Windows GBK 控制台 | 确保所有字符串 ASCII-safe |
| BLE 连接失败 | 设备未配对或 PL 级别错误 | 确认配对级别为 Encryption(1) |
""",
        },
        {
            "name": "安装与配置",
            "content": """# 安装与配置

## 运行要求

- Python 3.10+
- bleak (BLE 库)
- Windows 10/11 (蓝牙 4.0+)
- M5StickC Plus 已刷入 Buddy 固件

## 安装步骤

### 1. 安装 Python 依赖

```powershell
python -m pip install bleak
```

### 2. 安装 cdbb 包

```powershell
# 从项目目录运行
powershell -ExecutionPolicy Bypass -File setup.ps1
```

`setup.ps1` 完成以下操作：
1. `pip install bleak`
2. 复制 `cdbb/*.py` 到 Python site-packages
3. 运行 `cdbb install` 注入 Claude Code hook 配置

### 3. 手动安装 hook

```bash
cdbb install              # 拦截所有工具
cdbb install --tools Bash # 仅拦截 Bash
cdbb install --force      # 覆盖已有配置
```

### 4. Windows 配对修复

**关键**：Windows 蓝牙设置 UI 默认使用高保护级别。守护进程启动时会自动：
1. 检测已存在的高级别配对 (PL2/PL3)
2. 先解除配对
3. 以 Encryption (PL1) 级别重新配对

## 启动守护进程

### 方式一：开机自启动（推荐）

一次性配置，之后每次登录 Windows 和打开 Claude Code 都会自动拉起守护进程：

```powershell
powershell -ExecutionPolicy Bypass -File cdbb-autostart.ps1
```

**原理**：
- **Windows Startup 文件夹**：登录时通过 VBS 脚本静默启动（无需管理员权限）
- **Claude Code SessionStart hook**：打开 Claude Code 时自动检查，daemon 不在就拉起（兜底）
- **存活检查**：启动脚本先检测 TCP 127.0.0.1:19876 是否已有监听，避免重复启动

移除自动启动：

```powershell
powershell -ExecutionPolicy Bypass -File cdbb-autostart.ps1 -Unregister
```

### 方式二：使用启动脚本

```powershell
powershell -File cdbb-start.ps1
```

### 方式三：环境变量 + Python

```powershell
$env:CDBB_DEVICE_ID = "BluetoothLE#BluetoothLE14:4f:8a:7a:bb:b4-70:04:1d:d6:21:d1"
$env:CDBB_ADDR = "70:04:1D:D6:21:D1"
python -c "import cdbb.cli; cdbb.cli.main()" daemon -v
```

### 方式四：CLI 直接运行

```bash
cdbb daemon -v
```

## 环境变量

| 变量 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `CDBB_DEVICE_ID` | Windows 推荐 | 蓝牙设备 ID，用于 FromIdAsync 绕过广播扫描 | `BluetoothLE#BluetoothLE14:4f:...` |
| `CDBB_ADDR` | 可选 | MAC 地址，跳过扫描直接连接 | `70:04:1D:D6:21:D1` |
| `PYTHONIOENCODING` | Windows 推荐 | 避免 GBK 编码问题 | `utf-8` |
| `PYTHONUTF8` | Windows 推荐 | 强制 UTF-8 模式 | `1` |

## CLI 命令参考

| 命令 | 说明 |
|------|------|
| `cdbb daemon` | 启动守护进程 |
| `cdbb daemon -v` | 启动 + 详细日志 |
| `cdbb scan` | 扫描附近 Claude BLE 设备 |
| `cdbb status` | 检查守护进程是否运行 |
| `cdbb install` | 注入 Claude Code hook 配置 |
| `cdbb install --tools Bash Write` | 注入指定工具的 hook |
| `cdbb uninstall` | 移除 hook 配置 |

## 文件位置

| 文件 | 路径 |
|------|------|
| 安装目录 | `<site-packages>/cdbb/` |
| Hook 脚本 | `<site-packages>/cdbb/hook.py` |
| Claude Code 配置 | `~/.claude/settings.json` |
| 启动脚本 | `cdbb-start.ps1`（项目目录） |
| 安装脚本 | `setup.ps1`（项目目录） |
| 自启动注册 | `cdbb-autostart.ps1`（项目目录） |
| 守护进程启动器 | `cdbb-daemon-launcher.ps1`（项目目录） |
| 守护进程日志 | `%USERPROFILE%\\.claude\\logs\\cdbb-daemon.log` |

## GitHub

https://github.com/whoisjackchao-dot/Yes-engineer
""",
        },
        {
            "name": "开机自动启动机制",
            "content": """# 开机自动启动机制

## 架构

```
Windows 登录
  └─ Startup 文件夹 (VBS 脚本)
       └─ cdbb-daemon-launcher.ps1
            ├─ 检测 TCP 127.0.0.1:19876 是否已有监听
            ├─ 已有监听 → 退出 (避免重复启动)
            └─ 未在运行 → 启动 daemon → 等待 15s → 验证

Claude Code 启动
  └─ SessionStart hook
       └─ cdbb-daemon-launcher.ps1 (同上兜底)
```

## 双重保障

| 机制 | 触发时机 | 说明 |
|------|----------|------|
| Windows Startup 文件夹 | 每次用户登录 | VBS 脚本静默启动 PowerShell，无窗口 |
| SessionStart hook | 每次打开 Claude Code | 兜底检查，daemon 不在就拉起 |

## 实现

### cdbb-autostart.ps1

注册脚本流程：

1. 在 `%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup` 创建 VBS 文件
2. VBS 内容：`CreateObject("Wscript.Shell").Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File <launcher-path>", 0, False`
3. 同时立即运行一次并验证连接通达

```powershell
# 注册自动启动
powershell -ExecutionPolicy Bypass -File cdbb-autostart.ps1

# 移除自动启动
powershell -ExecutionPolicy Bypass -File cdbb-autostart.ps1 -Unregister
```

### cdbb-daemon-launcher.ps1

守护进程启动器（含存活检查）：

1. 设置环境变量 `CDBB_DEVICE_ID`、`CDBB_ADDR`、`PYTHONIOENCODING`、`PYTHONUTF8`
2. 先检测 `127.0.0.1:19876` 是否有 TCP 监听
3. 有监听 → 写日志退出，避免重复启动
4. 没有 → 执行 `python -c "import cdbb.cli; cdbb.cli.main()" daemon -v`
5. 等待 15 秒，验证 TCP 是否联通
6. 日志写入 `%USERPROFILE%\\.claude\\logs\\cdbb-daemon.log`

## VBS 原理

```vbscript
CreateObject("Wscript.Shell").Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File <launcher-path>", 0, False
```

- `-WindowStyle Hidden`：不显示窗口，静默运行
- `0`：不显示窗口
- `False`：脚本不等待即退出
- 无需管理员权限：在用户登录时自动执行

## 日志

路径：`%USERPROFILE%\\.claude\\logs\\cdbb-daemon.log`

日志示例：

```
2026-05-27 23:15:30  Daemon not running, starting...
2026-05-27 23:15:45  Daemon started successfully (PID: 12345)
2026-05-27 23:20:00  Daemon already running, nothing to do.
```
""",
        },
    ]

    # ── 3. 写入页面 ──────────────────────────────────────────
    used_ids = set()

    for i, page_spec in enumerate(pages):
        order = i + 1
        name = page_spec["name"]
        content = page_spec["content"]

        if order in existing_by_index:
            pid = existing_by_index[order]["id"]
            print(f"更新页面 #{order}: {name}...")
            r = api(f"/docs/{DOC_ID}/pages/{pid}", method="PUT",
                    body={"name": name, "content": content})
            if "error" in r:
                print(f"  [失败] {r.get('error')}")
            else:
                print(f"  [成功]")
            used_ids.add(pid)
        else:
            print(f"创建页面 #{order}: {name}...")
            r = api(f"/docs/{DOC_ID}/pages", method="POST",
                    body={"name": name, "content": content})
            if "error" in r:
                print(f"  [失败] {r.get('error')}")
            else:
                print(f"  [成功] id={r.get('id')}")
                used_ids.add(r.get("id"))

    # 4. 删除多余页面
    for p in existing_pages:
        if p["id"] not in used_ids:
            print(f"删除多余页面: {p.get('name', '?')}...")
            r = api(f"/docs/{DOC_ID}/pages/{p['id']}", method="DELETE")
            if r and "error" in r:
                print(f"  [失败] {r.get('error')}")
            else:
                print(f"  [成功]")

    print(f"\n文档更新完成！共处理 {len(pages)} 个页面")


if __name__ == "__main__":
    main()
