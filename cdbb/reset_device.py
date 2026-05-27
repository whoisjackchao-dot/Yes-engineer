"""Reset and verify Buddy device state."""
import asyncio
from winrt.windows.devices.bluetooth import BluetoothLEDevice, BluetoothCacheMode
from winrt.windows.devices.bluetooth.genericattributeprofile import (
    GattSession, GattSessionStatus,
)
from winrt.windows.devices.enumeration import (
    DeviceInformation, DeviceUnpairingResultStatus,
    DevicePairingKinds, DevicePairingProtectionLevel,
    DevicePairingResultStatus,
)
from bleak.backends.winrt.client import FutureLike
import uuid

device_id = "BluetoothLE#BluetoothLE14:4f:8a:7a:bb:b4-70:04:1d:d6:21:d1"
nus_uuid = uuid.UUID("6e400001-b5a3-f393-e0a9-e50e24dcca9e")

async def main():
    # Step 1: Get device
    print("Step 1: Getting device...")
    device = await BluetoothLEDevice.from_id_async(device_id)
    if device is None:
        print("FAILED: device is None")
        return
    print(f"  Name: {device.name}")
    print(f"  ConnectionStatus: {device.connection_status}")

    # Step 2: Check and fix pairing
    di = await DeviceInformation.create_from_id_async(device.device_information.id)
    print(f"  IsPaired: {di.pairing.is_paired}")
    print(f"  ProtectionLevel: {di.pairing.protection_level}")

    # Unpair to start clean
    if di.pairing.is_paired:
        result = await di.pairing.unpair_async()
        print(f"  Unpair result: {result.status}")

    # Close device and re-acquire
    device.close()
    await asyncio.sleep(2)

    print("\nStep 2: Re-acquiring device after clean...")
    device = await BluetoothLEDevice.from_id_async(device_id)
    print(f"  ConnectionStatus: {device.connection_status}")

    # Create GATT session
    print("\nStep 3: Creating GATT session...")
    session = await GattSession.from_device_id_async(device.bluetooth_device_id)
    print(f"  Session status: {session.session_status}")
    print(f"  Can maintain: {session.can_maintain_connection}")

    session.maintain_connection = True
    await asyncio.sleep(2)
    print(f"  Session status after wait: {session.session_status}")

    # Try service access
    print("\nStep 4: Accessing services...")
    result = await FutureLike(device.get_gatt_services_async())
    print(f"  Status: {result.status}")

    if result.status == 0:
        for svc in result.services:
            svc_uuid_str = str(svc.uuid)
            chars_result = await FutureLike(
                svc.get_characteristics_with_cache_mode_async(BluetoothCacheMode.UNCACHED)
            )
            print(f"  {svc_uuid_str}: chars_status={chars_result.status}, count={len(chars_result.characteristics)}")

            if "6e400001" in svc_uuid_str and chars_result.status == 0:
                for c in chars_result.characteristics:
                    props = c.characteristic_properties
                    print(f"    Char: {c.uuid} handle={c.attribute_handle} props={props}")

    session.maintain_connection = False
    session.close()
    device.close()
    print("\nDone. Device cleanup complete.")

asyncio.run(main())
