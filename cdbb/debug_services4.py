import asyncio
import uuid
from winrt.windows.devices.bluetooth import BluetoothLEDevice, BluetoothCacheMode
from winrt.windows.devices.bluetooth.genericattributeprofile import (
    GattSession, GattSessionStatus, GattDeviceService
)
from winrt.windows.devices.enumeration import (
    DeviceInformation, DeviceInformationCustomPairing,
    DevicePairingKinds, DevicePairingProtectionLevel,
    DevicePairingResultStatus,
)
from bleak.backends.winrt.client import FutureLike

nus_uuid = uuid.UUID("6e400001-b5a3-f393-e0a9-e50e24dcca9e")
device_id = "BluetoothLE#BluetoothLE14:4f:8a:7a:bb:b4-70:04:1d:d6:21:d1"

async def main():
    print("Step 1: Getting device...")
    device = await BluetoothLEDevice.from_id_async(device_id)
    print(f"  Name: {device.name}")
    print(f"  ConnectionStatus: {device.connection_status}")
    print(f"  DeviceInformation ID: {device.device_information.id}")

    # Check pairing status
    di = await DeviceInformation.create_from_id_async(device.device_information.id)
    print(f"  IsPaired: {di.pairing.is_paired}")
    print(f"  CanPair: {di.pairing.can_pair}")
    print(f"  ProtectionLevel: {di.pairing.protection_level}")

    # Try directly getting NUS characteristics by UUID without service enumeration
    print("\nStep 2: Trying direct characteristic access...")
    # Try getting all characteristics for NUS service using a raw approach
    nus_result = await FutureLike(device.get_gatt_services_for_uuid_async(nus_uuid))
    if nus_result.status == 0 and len(nus_result.services) > 0:
        svc = nus_result.services[0]
        print(f"  NUS service found, handle: {svc.attribute_handle}")

        # Try getting ALL characteristics
        chars_result = await FutureLike(svc.get_characteristics_async())
        print(f"  get_characteristics status: {chars_result.status}")

        # Try getting included services
        inc_result = await FutureLike(svc.get_included_services_async())
        print(f"  get_included_services status: {inc_result.status}")
    else:
        print(f"  NUS service status: {nus_result.status}")

    # Also try getting device information to see what's happening
    print("\nStep 3: Trying all services again with more detail...")
    result = await FutureLike(device.get_gatt_services_async())
    print(f"  All services status: {result.status}")
    for svc in result.services:
        print(f"  Service: {svc.uuid}, handle: {svc.attribute_handle}")

        if str(svc.uuid).startswith("6e400001"):
            print("    -> This is NUS! Trying all access methods...")

            # Method 1: Regular
            r1 = await FutureLike(svc.get_characteristics_async())
            print(f"    Method 1 (regular): status={r1.status}")

            # Method 2: UNCACHED
            r2 = await FutureLike(svc.get_characteristics_with_cache_mode_async(BluetoothCacheMode.UNCACHED))
            print(f"    Method 2 (UNCACHED): status={r2.status}")

            # Method 3: CACHED
            r3 = await FutureLike(svc.get_characteristics_with_cache_mode_async(BluetoothCacheMode.CACHED))
            print(f"    Method 3 (CACHED): status={r3.status}")

    device.close()

asyncio.run(main())
