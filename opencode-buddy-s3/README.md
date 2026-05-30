# Opencode-Buddy-S3

基于 M5Stick-S3 的 Opencode 安全审批终端。

## 架构
```
Opencode CLI (Hook) 
  └─ TCP (127.0.0.1:19876) 
       └─ Bridge (Python)
            └─ BLE (NUS)
                 └─ M5Stick-S3
```

## 功能
- A 键: 确认
- B 键: 下一个/向下滚动

## 开发说明
- `bridge/`: Python 桥接程序
- `firmware/`: M5Stick-S3 固件 (PlatformIO)
