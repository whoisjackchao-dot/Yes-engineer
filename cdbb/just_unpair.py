"""Just unpair the device."""
import asyncio
from winrt.windows.devices.bluetooth import BluetoothLEDevice
from winrt.windows.devices.enumeration import DeviceInformation

async def main():
    device_id = "BluetoothLE#BluetoothLE14:4f:8a:7a:bb:b4-70:04:1d:d6:21:d1"
    device = await BluetoothLEDevice.from_id_async(device_id)
    print(f"Device: {device.name}")
    di = await DeviceInformation.create_from_id_async(device.device_information.id)
    print(f"IsPaired: {di.pairing.is_paired}, PL: {di.pairing.protection_level}")
    if di.pairing.is_paired:
        r = await di.pairing.unpair_async()
        print(f"Unpair result: {r.status}")
    device.close()

asyncio.run(main())
