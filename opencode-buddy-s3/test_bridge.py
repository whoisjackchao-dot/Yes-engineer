import asyncio
import json

# 模拟固件行为
class MockDevice:
    def __init__(self, bridge):
        self.bridge = bridge
        self.current_id = None

    async def receive_request(self, data):
        msg = json.loads(data)
        self.current_id = msg.get("id")
        print(f"[Device] 收到请求: {self.current_id}")

    async def simulate_button(self, decision):
        if self.current_id:
            response = {"id": self.current_id, "decision": decision}
            print(f"[Device] 发送决策: {response}")
            self.bridge.on_notify(0, (json.dumps(response) + "\n").encode())
            self.current_id = None

# 模拟桥接器
class MockBridge:
    def __init__(self):
        self._pending_requests = {}
        self._rx_buf = bytearray()
    
    def on_notify(self, _sender, data):
        self._rx_buf.extend(data)
        while b'\n' in self._rx_buf:
            line, self._rx_buf = self._rx_buf.split(b'\n', 1)
            msg = json.loads(line.decode())
            rid = msg.get("id")
            decision = msg.get("decision")
            if rid in self._pending_requests:
                if not self._pending_requests[rid].future.done():
                    self._pending_requests[rid].future.set_result(decision)
                    print(f"[Bridge] 成功收到决策: {decision} for {rid}")

async def main():
    bridge = MockBridge()
    device = MockDevice(bridge)
    
    # 模拟发送请求
    req_id = "req_123"
    fut = asyncio.get_running_loop().create_future()
    bridge._pending_requests[req_id] = type('obj', (), {'future': fut})
    
    # 模拟设备收到请求
    await device.receive_request(json.dumps({"id": req_id, "tool": "test_tool"}))
    
    # 模拟用户按下A键
    await device.simulate_button("approve")
    
    # 校验结果
    result = await fut
    assert result == "approve"
    print("[Success] 闭环校验通过")

if __name__ == "__main__":
    asyncio.run(main())