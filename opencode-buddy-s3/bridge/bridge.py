import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger("opencode.bridge")

# NUS UUIDs
NUS_RX = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"

@dataclass
class PendingRequest:
    id: str
    future: asyncio.Future

class Bridge:
    def __init__(self, client):
        self.client = client
        self._pending_requests: Dict[str, PendingRequest] = {}
        self._write_lock = asyncio.Lock()
        self._rx_buf = bytearray()

    async def send_to_device(self, obj: dict):
        payload = (json.dumps(obj) + "\n").encode()
        async with self._write_lock:
            await self.client.write_gatt_char(NUS_RX, payload, response=True)

    def on_notify(self, _sender, data: bytearray):
        self._rx_buf.extend(data)
        while b'\n' in self._rx_buf:
            line, self._rx_buf = self._rx_buf.split(b'\n', 1)
            if not line: continue
            try:
                msg = json.loads(line.decode())
                rid = msg.get("id")
                decision = msg.get("decision")
                if rid in self._pending_requests:
                    if not self._pending_requests[rid].future.done():
                        self._pending_requests[rid].future.set_result(decision)
            except Exception as e:
                logger.error(f"设备消息解析失败: {e}")

    async def handle_hook_client(self, reader, writer):
        raw = await reader.readline()
        if not raw: return
        req = json.loads(raw.decode())
        rid = req.get("id", "unknown")
        
        # 创建 Future 等待设备决策
        fut = asyncio.get_running_loop().create_future()
        self._pending_requests[rid] = PendingRequest(id=rid, future=fut)
        
        # 推送请求给设备
        await self.send_to_device({"type": "request", **req})
        
        # 等待设备按键反馈
        try:
            decision = await asyncio.wait_for(fut, timeout=60.0)
            writer.write(json.dumps({"decision": decision}).encode() + b'\n')
        except asyncio.TimeoutError:
            writer.write(json.dumps({"decision": "deny", "error": "timeout"}).encode() + b'\n')
        finally:
            del self._pending_requests[rid]
            await writer.drain()
            writer.close()
