import asyncio
from bleak import BleakScanner

async def main():
    print("Scanning for BLE devices (10s)...")
    d = await BleakScanner.find_device_by_filter(
        lambda d, _: bool(d.name and d.name.startswith("Claude")),
        timeout=10.0,
    )
    if d:
        print(f"Found: {d.name} at {d.address}")
    else:
        print("NOT FOUND - device is not broadcasting")

asyncio.run(main())
