import asyncio
import uuid
from winrt.windows.devices.bluetooth import BluetoothLEDevice, BluetoothCacheMode
from winrt.windows.devices.bluetooth.genericattributeprofile import GattCommunicationStatus
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

    # Try getting only NUS service
    nus_uuid = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
    print(f"\n--- Trying to get NUS service directly ---")
    result = await FutureLike(device.get_gatt_services_for_uuid_async(uuid.UUID(nus_uuid)))
    print(f"get_gatt_services_for_uuid status: {result.status}")
    if result.status == 0:
        services = result.services
        print(f"  Found {len(services)} service(s)")
        for svc in services:
            print(f"  Service UUID: {svc.uuid}")

            # Try UNCACHED mode
            print(f"  Trying get_characteristics_with_cache_mode_async(UNCACHED)...")
            chars_result = await FutureLike(
                svc.get_characteristics_with_cache_mode_async(BluetoothCacheMode.UNCACHED)
            )
            print(f"  UNCACHED characteristics status: {chars_result.status}")

            if chars_result.status != 0:
                # Try CACHED mode
                print(f"  Trying get_characteristics_with_cache_mode_async(CACHED)...")
                chars_result = await FutureLike(
                    svc.get_characteristics_with_cache_mode_async(BluetoothCacheMode.CACHED)
                )
                print(f"  CACHED characteristics status: {chars_result.status}")

            if chars_result.status == 0:
                for char in chars_result.characteristics:
                    print(f"    Char UUID: {char.uuid}, handle: {char.attribute_handle}")

    device.close()

asyncio.run(main())
