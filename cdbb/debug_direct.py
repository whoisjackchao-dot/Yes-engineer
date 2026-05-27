import asyncio
import uuid
from winrt.windows.devices.bluetooth import BluetoothLEDevice, BluetoothCacheMode
from winrt.windows.devices.bluetooth.genericattributeprofile import GattSession
from bleak.backends.winrt.client import FutureLike

device_id = "BluetoothLE#BluetoothLE14:4f:8a:7a:bb:b4-70:04:1d:d6:21:d1"
rx_uuid = uuid.UUID("6e400002-b5a3-f393-e0a9-e50e24dcca9e")
tx_uuid = uuid.UUID("6e400003-b5a3-f393-e0a9-e50e24dcca9e")
nus_uuid = uuid.UUID("6e400001-b5a3-f393-e0a9-e50e24dcca9e")

async def main():
    # Try FromBluetoothAddressAsync - just to check
    print("=== Testing FromBluetoothAddressAsync ===")
    addr_int = int("70:04:1D:D6:21:D1".replace(":", ""), 16)
    dev = await BluetoothLEDevice.from_bluetooth_address_async(addr_int)
    if dev is None:
        print("FromBluetoothAddressAsync: FAILED (device not broadcasting)")
    else:
        print(f"FromBluetoothAddressAsync: SUCCESS - {dev.name}")
        dev.close()

    # Try FromIdAsync + direct characteristic UUID access
    print("\n=== Testing FromIdAsync + direct characteristic access ===")
    device = await BluetoothLEDevice.from_id_async(device_id)
    print(f"Device: {device.name}")

    # Get NUS service
    result = await FutureLike(device.get_gatt_services_for_uuid_async(nus_uuid))
    if result.status == 0 and len(result.services) > 0:
        svc = result.services[0]
        print(f"NUS service handle: {svc.attribute_handle}")

        # Try getting characteristics directly by UUID
        for label, char_uuid in [("RX", rx_uuid), ("TX", tx_uuid)]:
            r = await FutureLike(svc.get_characteristics_for_uuid_async(char_uuid))
            print(f"  {label} ({char_uuid}): status={r.status}, count={len(r.characteristics)}")
            if r.status == 0 and len(r.characteristics) > 0:
                for c in r.characteristics:
                    print(f"    handle={c.attribute_handle}, props={c.characteristic_properties}")

    # Try with GATT session
    print("\n=== Testing with GATT session ===")
    session = await GattSession.from_device_id_async(device.bluetooth_device_id)
    print(f"Session status: {session.session_status}")
    session.maintain_connection = True
    await asyncio.sleep(1)
    print(f"Session status after maintain: {session.session_status}")

    result2 = await FutureLike(device.get_gatt_services_for_uuid_async(nus_uuid))
    if result2.status == 0 and len(result2.services) > 0:
        svc2 = result2.services[0]
        for label, char_uuid in [("RX", rx_uuid), ("TX", tx_uuid)]:
            r = await FutureLike(svc2.get_characteristics_for_uuid_async(char_uuid))
            print(f"  {label}: status={r.status}, count={len(r.characteristics)}")

    session.maintain_connection = False
    session.close()
    device.close()

asyncio.run(main())
