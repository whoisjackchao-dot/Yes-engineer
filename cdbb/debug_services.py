import asyncio
from winrt.windows.devices.bluetooth import BluetoothLEDevice, BluetoothCacheMode
from bleak.backends.winrt.client import FutureLike

async def main():
    device_id = "BluetoothLE#BluetoothLE14:4f:8a:7a:bb:b4-70:04:1d:d6:21:d1"
    print(f"Connecting via FromIdAsync: {device_id}")
    device = await BluetoothLEDevice.from_id_async(device_id)
    if device is None:
        print("FAILED: device is None")
        return
    print(f"Device: {device.name}")
    print(f"ConnectionStatus: {device.connection_status}")

    result = await FutureLike(device.get_gatt_services_async())
    print(f"GATT services status: {result.status}")
    services = result.services
    print(f"Number of services: {len(services)}")

    for svc in services:
        print(f"  Service UUID: {svc.uuid}")
        chars_result = await FutureLike(svc.get_characteristics_async())
        print(f"    Characteristics status: {chars_result.status}")
        for char in chars_result.characteristics:
            print(f"      Char UUID: {char.uuid}, handle: {char.attribute_handle}, props: {char.characteristic_properties}")

    device.close()

asyncio.run(main())
