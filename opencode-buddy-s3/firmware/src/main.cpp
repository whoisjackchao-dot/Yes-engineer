#include <M5Unified.h>
#include <NimBLEDevice.h>
#include <ArduinoJson.h>

// BLE NUS UUIDs
#define SERVICE_UUID           "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
#define CHARACTERISTIC_UUID_RX "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
#define CHARACTERISTIC_UUID_TX "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

NimBLECharacteristic *pCharacteristicTX;
bool deviceConnected = false;

class MyServerCallbacks : public NimBLEServerCallbacks {
    void onConnect(NimBLEServer* pServer) { deviceConnected = true; }
    void onDisconnect(NimBLEServer* pServer) { deviceConnected = false; }
};

String current_id = "";

class MyCallbacks : public NimBLECharacteristicCallbacks {
    void onWrite(NimBLECharacteristic *pCharacteristic) {
        std::string value = pCharacteristic->getValue();
        if (value.length() > 0) {
            JsonDocument doc;
            deserializeJson(doc, value);
            if (doc.containsKey("id")) {
                current_id = doc["id"].as<String>();
                // TODO: 更新 M5 屏幕显示 doc["tool"]
            }
        }
    }
};

void setup() {
    auto cfg = M5.config();
    M5.begin(cfg);
    
    // BLE 初始化
    NimBLEDevice::init("Claude-S3");
    NimBLEServer *pServer = NimBLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());
    
    NimBLEService *pService = pServer->createService(SERVICE_UUID);
    pCharacteristicTX = pService->createCharacteristic(CHARACTERISTIC_UUID_TX, NIMBLE_PROPERTY::NOTIFY);
    
    NimBLECharacteristic *pCharacteristicRX = pService->createCharacteristic(CHARACTERISTIC_UUID_RX, NIMBLE_PROPERTY::WRITE);
    pCharacteristicRX->setCallbacks(new MyCallbacks());
    
    pService->start();
    NimBLEAdvertising *pAdvertising = NimBLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->start();
}

void loop() {
    M5.update();
    
    if (current_id != "") {
        if (M5.BtnA.wasPressed()) {
             pCharacteristicTX->setValue("{\"id\":\"" + current_id + "\",\"decision\":\"approve\"}");
             pCharacteristicTX->notify();
             current_id = ""; // 重置状态
        }
        
        if (M5.BtnB.wasPressed()) {
             pCharacteristicTX->setValue("{\"id\":\"" + current_id + "\",\"decision\":\"deny\"}");
             pCharacteristicTX->notify();
             current_id = ""; // 重置状态
        }
    }
}
