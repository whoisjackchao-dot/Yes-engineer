import asyncio
import uuid
from winrt.windows.devices.bluetooth import BluetoothLEDevice, BluetoothCacheMode
from winrt.windows.devices.bluetooth.genericattributeprofile import (
    GattSession, GattSessionStatus,
)
from winrt.windows.devices.enumeration import (
    DeviceInformation, DeviceUnpairingResultStatus,
)
from bleak.backends.winrt.client import FutureLike

device_id = "BluetoothLE#BluetoothLE14:4f:8a:7a:bb:b4-70:04:1d:d6:21:d1"
nus_uuid = uuid.UUID("6e400001-b5a3-f393-e0a9-e50e24dcca9e")

async def main():
    # Get device
    device = await BluetoothLEDevice.from_id_async(device_id)
    print(f"Device: {device.name}")

    # Check pairing
    di = await DeviceInformation.create_from_id_async(device.device_information.id)
    print(f"IsPaired: {di.pairing.is_paired}")

    if di.pairing.is_paired:
        print("Unpairing device...")
        result = await di.pairing.unpair_async()
        print(f"Unpair status: {result.status}")
        if result.status == DeviceUnpairingResultStatus.UNPAIRED:
            print("Device unpaired successfully!")
        else:
            print(f"Unpair failed with status: {result.status}")
            device.close()
            return

    # Re-open device (unpairing might have closed it)
    device.close()
    await asyncio.sleep(1)

    print("\nRe-opening device after unpair...")
    device = await BluetoothLEDevice.from_id_async(device_id)
    print(f"ConnectionStatus: {device.connection_status}")

    if device is None:
        print("Device is None after unpair!")
        return

    # Try accessing NUS again
    print("Trying NUS service...")
    result = await FutureLike(device.get_gatt_services_for_uuid_async(nus_uuid))
    print(f"NUS service status: {result.status}")
    if result.status == 0:
        svc = result.services[0]
        chars_result = await FutureLike(svc.get_characteristics_async())
        print(f"Characteristics status: {chars_result.status} (0=Success, 1=Unreachable, 2=ProtocolError, 3=AccessDenied)")

    device.close()

asyncio.run(main())
