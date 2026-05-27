import asyncio
import uuid
from winrt.windows.devices.bluetooth import BluetoothLEDevice, BluetoothCacheMode
from winrt.windows.devices.bluetooth.genericattributeprofile import (
    GattSession, GattSessionStatus,
)
from winrt.windows.devices.enumeration import (
    DeviceInformation, DevicePairingResultStatus,
    DevicePairingKinds, DevicePairingProtectionLevel,
)
from bleak.backends.winrt.client import FutureLike

device_id = "BluetoothLE#BluetoothLE14:4f:8a:7a:bb:b4-70:04:1d:d6:21:d1"
nus_uuid = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"

async def main():
    # Get device
    device = await BluetoothLEDevice.from_id_async(device_id)
    print(f"Device: {device.name}")
    print(f"ConnectionStatus: {device.connection_status}")
    print(f"DeviceInformation.ID: {device.device_information.id}")

    # Check pairing
    di = await DeviceInformation.create_from_id_async(device.device_information.id)
    print(f"\nPairing info:")
    print(f"  IsPaired: {di.pairing.is_paired}")
    print(f"  CanPair: {di.pairing.can_pair}")
    print(f"  ProtectionLevel: {di.pairing.protection_level}")

    # If not paired, try pairing
    if not di.pairing.is_paired:
        print("\nDevice is not paired. Attempting to pair...")
        ceremony = DevicePairingKinds.CONFIRM_ONLY
        custom_pairing = di.pairing.custom

        def handler(sender, args):
            print("  Pairing request received, accepting...")
            args.accept()

        token = custom_pairing.add_pairing_requested(handler)
        try:
            for level in (
                DevicePairingProtectionLevel.ENCRYPTION_AND_AUTHENTICATION,
                DevicePairingProtectionLevel.ENCRYPTION,
            ):
                result = await FutureLike(
                    custom_pairing.pair_with_protection_level_async(ceremony, level)
                )
                print(f"  Pair result (level={level}): {result.status}")
                if result.status in (
                    DevicePairingResultStatus.PAIRED,
                    DevicePairingResultStatus.ALREADY_PAIRED,
                ):
                    print(f"  Paired with protection level: {result.protection_level_used}")
                    break
            else:
                result = await FutureLike(custom_pairing.pair_async(ceremony))
                print(f"  Pair result (default): {result.status}")
        finally:
            custom_pairing.remove_pairing_requested(token)

    # Re-check pairing
    di2 = await DeviceInformation.create_from_id_async(device.device_information.id)
    print(f"\nAfter pairing attempt:")
    print(f"  IsPaired: {di2.pairing.is_paired}")
    print(f"  ProtectionLevel: {di2.pairing.protection_level}")

    # Try services with a GATT session
    print("\nCreating GATT session...")
    session = await GattSession.from_device_id_async(device.bluetooth_device_id)
    print(f"Session status: {session.session_status}")
    session.maintain_connection = True
    await asyncio.sleep(1)
    print(f"Session status after maintain: {session.session_status}")

    # Try NUS again
    print("\nTrying NUS service access...")
    result = await FutureLike(device.get_gatt_services_async())
    print(f"All services: {result.status}, count={len(result.services)}")
    for svc in result.services:
        svc_uuid = str(svc.uuid)
        chars_result = await FutureLike(svc.get_characteristics_async())
        print(f"  {svc_uuid}: chars_status={chars_result.status}, count={len(chars_result.characteristics)}")

    session.maintain_connection = False
    session.close()
    device.close()

asyncio.run(main())
