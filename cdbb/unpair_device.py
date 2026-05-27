"""Unpair Claude-21D1 from Windows to fix NUS ACCESS_DENIED."""
import asyncio
from winrt.windows.devices.bluetooth import BluetoothLEDevice
from winrt.windows.devices.enumeration import (
    DeviceInformation, DeviceUnpairingResultStatus,
)
from bleak.backends.winrt.client import FutureLike

device_id = "BluetoothLE#BluetoothLE14:4f:8a:7a:bb:b4-70:04:1d:d6:21:d1"

async def main():
    device = await BluetoothLEDevice.from_id_async(device_id)
    if device is None:
        print("Device not found")
        return

    print(f"Device: {device.name}")

    # Check current pairing state
    di = await DeviceInformation.create_from_id_async(device.device_information.id)
    print(f"IsPaired: {di.pairing.is_paired}")
    print(f"ProtectionLevel: {di.pairing.protection_level}")

    if not di.pairing.is_paired:
        print("Device is not paired. Nothing to do.")
        device.close()
        return

    print("Unpairing...")
    result = await di.pairing.unpair_async()
    status_names = {
        0: "UNPAIRED",
        1: "ALREADY_UNPAIRED",
        2: "FAILED",
        3: "ACCESS_DENIED",
    }
    status_name = status_names.get(result.status, f"UNKNOWN({result.status})")
    print(f"Result: {status_name}")

    device.close()

    if result.status in (0, 1):  # UNPAIRED or ALREADY_UNPAIRED
        print("\nSUCCESS: Device unpaired. Ready for fresh connection.")
    else:
        print(f"\nFAILED to unpair: {status_name}")

asyncio.run(main())
