import asyncio
from winrt.windows.devices.bluetooth import BluetoothLEDevice
from winrt.windows.devices.enumeration import (
    DeviceInformation, DeviceInformationKind,
)
from bleak.backends.winrt.client import FutureLike

device_id = "BluetoothLE#BluetoothLE14:4f:8a:7a:bb:b4-70:04:1d:d6:21:d1"
mac_addr = "70:04:1D:D6:21:D1"

async def main():
    # Method 1: FindAllAsync with BLE selector
    print("=== Method 1: DeviceInformation.FindAllAsync ===")
    # Use the standard BLE device selector
    selector = "(System.Devices.Aep.ProtocolId:=\"{bb7bb05e-5972-42b5-94fc-76eaa7084d49}\")"
    result = await FutureLike(
        DeviceInformation.find_all_async(selector, [], DeviceInformationKind.ASSOCIATION_ENDPOINT)
    )
    print(f"Found {len(result)} devices")
    for di in result:
        print(f"  {di.name:30s} id={di.id:60s} paired={di.pairing.is_paired}")

    # Method 2: Try FromBluetoothAddressAsync with the known address
    print(f"\n=== Method 2: FromBluetoothAddressAsync({mac_addr}) ===")
    addr_int = int(mac_addr.replace(":", ""), 16)
    device = await BluetoothLEDevice.from_bluetooth_address_async(addr_int)
    if device is None:
        print("FAILED: from_bluetooth_address_async returned None")
    else:
        print(f"SUCCESS: {device.name}, ConnectionStatus={device.connection_status}")
        device.close()

    # Method 3: After FindAllAsync, try FromBluetoothAddressAsync again
    print(f"\n=== Method 3: FromBluetoothAddressAsync after FindAllAsync ===")
    selector2 = "System.Devices.Aep.ProtocolId:=\"{bb7bb05e-5972-42b5-94fc-76eaa7084d49}\""
    result2 = await FutureLike(
        DeviceInformation.find_all_async(selector2)
    )
    print(f"FindAllAsync returned {len(result2)} devices")
    for di in result2:
        if di.name == "Claude-21D1":
            print(f"  Found: {di.name} id={di.id} paired={di.pairing.is_paired}")

    device2 = await BluetoothLEDevice.from_bluetooth_address_async(addr_int)
    if device2 is None:
        print("STILL FAILED: from_bluetooth_address_async returned None")
    else:
        print(f"SUCCESS: {device2.name}")
        device2.close()

asyncio.run(main())
