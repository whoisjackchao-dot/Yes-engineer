"""
ClickUp MCP 服务器 — 通过 MCP 协议读写 ClickUp Docs

协议: JSON-RPC 2.0 over stdio
工具:
  - update_doc(doc_id, pages) — 替换文档的全部页面内容
  - list_pages(doc_id) — 列出文档的所有页面
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
API_BASE = f"https://api.clickup.com/api/v3/workspaces/{WORKSPACE_ID}"


# ── HTTP 请求 ──────────────────────────────────────────────────────────────────

def _api(path: str, method: str = "GET", body: dict | None = None) -> Any:
    url = f"{API_BASE}{path}"
    headers = {
        "Authorization": API_TOKEN,
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        return {"error": f"HTTP {e.code}: {err_body}"}
    except Exception as e:
        return {"error": str(e)}


# ── ClickUp Docs API ───────────────────────────────────────────────────────────

def get_pages(doc_id: str) -> list[dict]:
    """获取文档下的所有页面。"""
    result = _api(f"/docs/{doc_id}/pages")
    if isinstance(result, dict) and "error" in result:
        return []
    if isinstance(result, dict) and "value" in result:
        return result["value"]
    # Some versions return the list directly
    if isinstance(result, list):
        return result
    return []


def get_page(doc_id: str, page_id: str) -> dict:
    """获取单个页面的详细信息。"""
    return _api(f"/docs/{doc_id}/pages/{page_id}")


def update_page(doc_id: str, page_id: str, name: str, content: str) -> dict:
    """更新页面的名称和内容（Markdown 格式）。"""
    return _api(
        f"/docs/{doc_id}/pages/{page_id}",
        method="PUT",
        body={"name": name, "content": content},
    )


def create_page(doc_id: str, name: str, content: str) -> dict:
    """创建新的页面。"""
    return _api(
        f"/docs/{doc_id}/pages",
        method="POST",
        body={"name": name, "content": content},
    )


def delete_page(doc_id: str, page_id: str) -> dict:
    """删除页面。"""
    result = _api(f"/docs/{doc_id}/pages/{page_id}", method="DELETE")
    if not result:  # empty response = success
        return {"ok": True}
    return result


def replace_all_pages(doc_id: str, pages: list[dict]) -> list[str]:
    """
    替换文档的全部页面内容。

    pages: [{"name": str, "content": str}, ...]
    返回操作日志。
    """
    logs = []
    existing = get_pages(doc_id)
    existing_by_index = {p.get("order_index", 99): p for p in existing}

    used_ids = set()

    # 按顺序更新或创建
    for i, page_spec in enumerate(pages):
        name = page_spec.get("name", f"Page {i+1}")
        content = page_spec.get("content", "")

        order = i + 1
        if order in existing_by_index:
            pid = existing_by_index[order]["id"]
            r = update_page(doc_id, pid, name, content)
            if "error" in r:
                logs.append(f"[ERROR] 更新页面 #{order} '{name}': {r['error']}")
            else:
                logs.append(f"[OK] 更新页面 #{order} '{name}'")
            used_ids.add(pid)
        else:
            r = create_page(doc_id, name, content)
            if "error" in r:
                logs.append(f"[ERROR] 创建页面 '{name}': {r['error']}")
            else:
                logs.append(f"[OK] 创建页面 '{name}' (id={r.get('id')})")
                used_ids.add(r.get("id"))

    # 删除多余的页面
    for p in existing:
        if p["id"] not in used_ids:
            r = delete_page(doc_id, p["id"])
            if "error" not in r:
                logs.append(f"[OK] 删除多余页面 '{p.get('name', '?')}'")
            else:
                logs.append(f"[WARN] 删除页面 '{p.get('name', '?')}' 失败: {r['error']}")

    return logs


# ── MCP 协议处理 ──────────────────────────────────────────────────────────────

_TOOLS = [
    {
        "name": "list_pages",
        "description": "列出 ClickUp 文档下的所有页面",
        "inputSchema": {
            "type": "object",
            "properties": {
                "doc_id": {
                    "type": "string",
                    "description": "ClickUp 文档 ID",
                },
            },
            "required": ["doc_id"],
        },
    },
    {
        "name": "replace_all_pages",
        "description": "替换文档的全部页面内容（更新已有页面，创建新页面，删除多余页面）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "doc_id": {
                    "type": "string",
                    "description": "ClickUp 文档 ID",
                },
                "pages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["name", "content"],
                    },
                    "description": "页面列表，每个页面包含 name 和 Markdown content",
                },
            },
            "required": ["doc_id", "pages"],
        },
    },
]


# ── MCP JSON-RPC 处理 ──────────────────────────────────────────────────────────

def _handle_request(req: dict) -> dict:
    method = req.get("method")
    params = req.get("params", {})
    req_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "clickup-mcp-server", "version": "0.1.0"},
            },
        }

    if method == "listTools":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": _TOOLS}}

    if method == "callTool":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        if tool_name == "list_pages":
            doc_id = tool_args.get("doc_id", "2kzmyhtx-878")
            pages = get_pages(doc_id)
            page_list = "\n".join(
                f"  #{p.get('order_index')} {p.get('name')} (id={p.get('id')})"
                for p in sorted(pages, key=lambda x: x.get("order_index", 99))
            )
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": f"文档共有 {len(pages)} 个页面:\n{page_list}"}
                    ],
                },
            }

        if tool_name == "replace_all_pages":
            doc_id = tool_args.get("doc_id", "2kzmyhtx-878")
            pages = tool_args.get("pages", [])
            logs = replace_all_pages(doc_id, pages)
            summary = "\n".join(logs)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": f"文档更新完成:\n{summary}"}
                    ],
                },
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": f"未知工具: {tool_name}"}],
                "isError": True,
            },
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"content": [{"type": "text", "text": f"未知方法: {method}"}]},
    }


def main() -> None:
    if not API_TOKEN:
        print("错误: 请设置 CLICKUP_API_TOKEN 环境变量", file=sys.stderr)
        sys.exit(1)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = _handle_request(req)
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
