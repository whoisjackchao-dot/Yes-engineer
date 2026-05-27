import asyncio
import uuid
from winrt.windows.devices.bluetooth import BluetoothLEDevice, BluetoothCacheMode
from winrt.windows.devices.bluetooth.genericattributeprofile import GattSession, GattSessionStatus
from bleak.backends.winrt.client import FutureLike

async def main():
    device_id = "BluetoothLE#BluetoothLE14:4f:8a:7a:bb:b4-70:04:1d:d6:21:d1"

    # Step 1: Get device
    print("Step 1: Getting device via FromIdAsync...")
    device = await BluetoothLEDevice.from_id_async(device_id)
    print(f"  ConnectionStatus before: {device.connection_status}")

    # Step 2: Check if we need to disconnect
    if device.connection_status == 1:
        print("  Device is already connected at OS level")

        # Try creating a GATT session to take control
        print("\nStep 2: Creating GATT session...")
        session = await GattSession.from_device_id_async(device.bluetooth_device_id)
        print(f"  Session status: {session.session_status}")
        print(f"  Can maintain connection: {session.can_maintain_connection}")

        session.maintain_connection = True
        print("  Set maintain_connection = True")

        # Wait briefly for session to become active
        await asyncio.sleep(1)
        print(f"  Session status after: {session.session_status}")

        # Now try access NUS characteristics
        print("\nStep 3: Trying to access NUS service with active session...")
        nus_uuid = uuid.UUID("6e400001-b5a3-f393-e0a9-e50e24dcca9e")
        result = await FutureLike(device.get_gatt_services_for_uuid_async(nus_uuid))
        print(f"  NUS service status: {result.status}")

        if result.status == 0:
            svc = result.services[0]
            chars_result = await FutureLike(
                svc.get_characteristics_with_cache_mode_async(BluetoothCacheMode.UNCACHED)
            )
            print(f"  Characteristics status: {chars_result.status}")

        session.maintain_connection = False
        session.close()

    device.close()

asyncio.run(main())
