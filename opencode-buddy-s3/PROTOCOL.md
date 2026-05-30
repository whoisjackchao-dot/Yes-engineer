# BLE 通信协议 (Opencode ↔ Bridge ↔ M5Stick-S3)

## 1. 结构概述
通信使用 Nordic UART Service (NUS)，所有数据包均为 JSON 格式，每行以 `\n` 结尾。

## 2. 桥接器 -> 设备 (TX: 主机向设备)
用于推送审批请求或状态：
```json
{
  "type": "request",
  "id": "unique_request_id",
  "tool": "ToolName",
  "hint": "Brief description"
}
```

## 3. 设备 -> 桥接器 (RX: 设备向主机)
用于回传用户审批决策：
```json
{
  "id": "unique_request_id",
  "decision": "approve" 
}
```
*   `approve`: A键按下，确认审批。
*   `down`: B键按下，触发滚动/忽略（取决于固件逻辑）。

## 4. 桥接器 -> Opencode (TCP)
```json
{
  "decision": "approve"
}
```
