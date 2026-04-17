import asyncio
from bleak import BleakScanner, BleakClient

BLE_MAC = "f2:4f:18:a6:f7:76"
DEVICE_NAME = "Arduino"

CHAR_UUID_X = "19B10001-E8F2-537E-4F6C-D104768A1214"
CHAR_UUID_Y = "19B10002-E8F2-537E-4F6C-D104768A1214"
CHAR_UUID_Z = "19B10003-E8F2-537E-4F6C-D104768A1214"


async def connect_device():
    # Try MAC address first
    try:
        print("Trying MAC address...")
        client = BleakClient(BLE_MAC)
        await client.connect()

        if client.is_connected:
            print("Connected using MAC address")
            return client

    except Exception as e:
        print("MAC connection failed:", e)

    # Fallback to scanning by name
    print("Scanning for device by name...")

    devices = await BleakScanner.discover()

    for d in devices:
        if d.name == DEVICE_NAME:
            print("Found device:", d)
            client = BleakClient(d.address)
            await client.connect()
            return client

    raise Exception("Device not found")


async def read_imu():
    client = await connect_device()

    async with client:
        print("Connected!")

        while True:
            x = (await client.read_gatt_char(CHAR_UUID_X)).decode()
            y = (await client.read_gatt_char(CHAR_UUID_Y)).decode()
            z = (await client.read_gatt_char(CHAR_UUID_Z)).decode()

            print(f"X:{x}  Y:{y}  Z:{z}")

            await asyncio.sleep(0.05)


if __name__ == "__main__":
    asyncio.run(read_imu())
