"""
cdbb.cli — 命令行入口

用法:
  cdbb daemon          启动守护进程（连接 BLE 设备，监听 Unix Socket）
  cdbb scan            扫描附近的 Claude BLE 设备并打印地址
  cdbb install         自动注入 Claude Code hook 配置
  cdbb uninstall       移除 Claude Code hook 配置
  cdbb status          检查守护进程是否在线
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import socket
import sys
from pathlib import Path

from cdbb import __version__


# ── 日志配置 ──────────────────────────────────────────────────────────────────

def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


# ── 子命令：daemon ─────────────────────────────────────────────────────────────

def cmd_daemon(args: argparse.Namespace) -> None:
    _setup_logging(args.verbose)
    from cdbb.bridge import run
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


# ── 子命令：scan ──────────────────────────────────────────────────────────────

def cmd_scan(_args: argparse.Namespace) -> None:
    _setup_logging()

    async def _scan() -> None:
        from bleak import BleakScanner
        print("Scanning for BLE devices (10s)...\n")
        devices = await BleakScanner.discover(timeout=10.0)
        found = False
        for d in sorted(devices, key=lambda x: x.name or ""):
            marker = " <-- cdbb compatible" if (d.name or "").startswith("Claude") else ""
            print(f"  {d.address}  {d.name or '(no name)'}{marker}")
            if marker:
                found = True
        if not found:
            print("\nNo Claude-compatible devices found. Check device is on and in range.")
        else:
            print(f"\nTip: use CDBB_ADDR=<addr> cdbb daemon to connect directly")

    asyncio.run(_scan())


# ── 子命令：status ─────────────────────────────────────────────────────────────

def cmd_status(_args: argparse.Namespace) -> None:
    from cdbb.bridge import SOCKET_PATH, SOCKET_HOST, SOCKET_PORT

    if SOCKET_PATH is not None:
        sock_target = SOCKET_PATH
        if not Path(sock_target).exists():
            print("cdbb daemon: not running (socket file not found)")
            sys.exit(1)

        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(1.0)
            s.connect(sock_target)
            s.close()
            print("cdbb daemon: running")
        except (ConnectionRefusedError, socket.timeout, OSError):
            print("cdbb daemon: socket exists but not responding (may have crashed)")
            sys.exit(1)
    else:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            s.connect((SOCKET_HOST, SOCKET_PORT))
            s.close()
            print("cdbb daemon: running")
        except (ConnectionRefusedError, socket.timeout, OSError):
            print("cdbb daemon: not running")
            sys.exit(1)


# ── 子命令：install ────────────────────────────────────────────────────────────

def cmd_install(args: argparse.Namespace) -> None:
    _setup_logging()

    hook_script = Path(sys.executable).parent / "cdbb-hook"
    # 如果是 uv 安装，尝试找到 hook.py 的绝对路径
    hook_py = Path(__file__).parent / "hook.py"

    # 优先用已安装的 entry point，回退到直接调用 hook.py
    if hook_script.exists():
        command = str(hook_script)
    else:
        command = f"{sys.executable} {hook_py}"

    settings_path = Path.home() / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    # 读取现有配置
    existing: dict = {}
    if settings_path.exists():
        try:
            existing = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            print(f"Warning: cannot parse {settings_path}, will create new file")

    # 构造 hook 配置
    hook_entry = {
        "type": "command",
        "command": command,
        "timeout": 120,
    }

    # 决定 matcher：默认覆盖所有工具，可通过 --tools 限定
    matchers = args.tools if args.tools else [""]  # "" = 匹配所有

    hooks_block = existing.setdefault("hooks", {})
    permission_hooks = hooks_block.setdefault("PermissionRequest", [])

    # 检查是否已存在 cdbb 条目
    already = any(
        h.get("command", "").find("cdbb") >= 0
        for entry in permission_hooks
        for h in entry.get("hooks", [])
    )
    if already and not args.force:
        print("cdbb hook already exists. Use --force to overwrite.")
        return

    # 移除旧条目后追加新条目
    permission_hooks[:] = [
        e for e in permission_hooks
        if not any(h.get("command", "").find("cdbb") >= 0 for h in e.get("hooks", []))
    ]

    for matcher in matchers:
        entry: dict = {"hooks": [hook_entry]}
        if matcher:
            entry["matcher"] = matcher
        permission_hooks.append(entry)

    settings_path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"[OK] cdbb hook written to {settings_path}")
    print(f"  Command: {command}")
    print(f"  Scope: {'all tools' if not args.tools else ', '.join(args.tools)}")
    print()
    print("Next: run 'cdbb daemon' to start, then launch Claude Code.")


# ── 子命令：uninstall ─────────────────────────────────────────────────────────

def cmd_uninstall(_args: argparse.Namespace) -> None:
    settings_path = Path.home() / ".claude" / "settings.json"
    if not settings_path.exists():
        print("Claude Code settings file not found.")
        return

    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Failed to read settings: {e}")
        sys.exit(1)

    hooks_block = data.get("hooks", {})
    permission_hooks = hooks_block.get("PermissionRequest", [])

    before = len(permission_hooks)
    permission_hooks[:] = [
        e for e in permission_hooks
        if not any(h.get("command", "").find("cdbb") >= 0 for h in e.get("hooks", []))
    ]
    after = len(permission_hooks)

    if before == after:
        print("No cdbb hook entries found.")
        return

    settings_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[OK] Removed {before - after} cdbb hook(s) from {settings_path}")


# ── 参数解析 ──────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cdbb",
        description="claude-desktop-buddy-bridge - BLE physical approval button for Claude Code CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cdbb scan                    # Scan nearby BLE devices
  cdbb install                 # Inject hook (all tools)
  cdbb install --tools Bash    # Only intercept Bash
  cdbb daemon                  # Start the daemon
  cdbb daemon -v               # Verbose debug logging
  cdbb status                  # Check daemon status
  cdbb uninstall               # Remove hook
  CDBB_ADDR=XX:XX:XX:XX cdbb daemon   # Skip scan
""",
    )
    parser.add_argument("-V", "--version", action="version", version=f"claude-desktop-buddy-bridge {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    # daemon
    p_daemon = sub.add_parser("daemon", help="Start the BLE daemon")
    p_daemon.add_argument("-v", "--verbose", action="store_true", help="Verbose debug logging")
    p_daemon.set_defaults(func=cmd_daemon)

    # scan
    p_scan = sub.add_parser("scan", help="Scan for nearby Claude BLE devices")
    p_scan.set_defaults(func=cmd_scan)

    # status
    p_status = sub.add_parser("status", help="Check if daemon is running")
    p_status.set_defaults(func=cmd_status)

    # install
    p_install = sub.add_parser("install", help="Auto-inject Claude Code hook config")
    p_install.add_argument(
        "--tools", nargs="+", metavar="TOOL",
        help="Tool names to intercept (default: all). e.g. --tools Bash Write",
    )
    p_install.add_argument("--force", action="store_true", help="Force overwrite existing config")
    p_install.set_defaults(func=cmd_install)

    # uninstall
    p_uninstall = sub.add_parser("uninstall", help="Remove Claude Code hook config")
    p_uninstall.set_defaults(func=cmd_uninstall)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
