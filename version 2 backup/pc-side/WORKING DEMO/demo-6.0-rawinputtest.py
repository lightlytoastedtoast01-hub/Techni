import asyncio
from bleak import BleakScanner, BleakClient
import pygame
import math
import time

# ------------------- BLE SETTINGS -------------------
BLE_MAC = "f2:4f:18:a6:f7:76"
DEVICE_NAME = "Arduino"

CHAR_UUID_X = "19B10001-E8F2-537E-4F6C-D104768A1214"
CHAR_UUID_Y = "19B10002-E8F2-537E-4F6C-D104768A1214"
CHAR_UUID_Z = "19B10003-E8F2-537E-4F6C-D104768A1214"

async def connect_device():
    try:
        print("Trying MAC address...")
        client = BleakClient(BLE_MAC)
        await client.connect()
        if client.is_connected:
            print("Connected using MAC address")
            return client
    except Exception as e:
        print("MAC connection failed:", e)

    print("Scanning for device by name...")
    devices = await BleakScanner.discover()
    for d in devices:
        if d.name == DEVICE_NAME:
            print("Found device:", d)
            client = BleakClient(d.address)
            await client.connect()
            return client
    raise Exception("Device not found")

# ------------------- PYGAME SETTINGS -------------------
pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

raw_strokes = []
smooth_strokes = []
current_raw = []
current_smooth = []

mouse_down = True  # we use pen input, always "down"
running = True

brush_x = None
brush_y = None
radius = 50
follow = 0.15

# ------------------- CATMULL-ROM SPLINE -------------------
def catmull_rom(points, steps=8):
    if len(points) < 4:
        return points
    curve = []
    for i in range(1, len(points)-2):
        p0, p1, p2, p3 = points[i-1], points[i], points[i+1], points[i+2]
        for j in range(steps):
            t = j / steps
            t2, t3 = t*t, t*t*t
            x = 0.5 * ((2*p1[0]) + (-p0[0]+p2[0])*t + (2*p0[0]-5*p1[0]+4*p2[0]-p3[0])*t2 + (-p0[0]+3*p1[0]-3*p2[0]+p3[0])*t3)
            y = 0.5 * ((2*p1[1]) + (-p0[1]+p2[1])*t + (2*p0[1]-5*p1[1]+4*p2[1]-p3[1])*t2 + (-p0[1]+3*p1[1]-3*p2[1]+p3[1])*t3)
            curve.append((x, y))
    curve.append(points[-2])
    curve.append(points[-1])
    return curve

def draw_stroke(surface, points):
    if len(points) < 2:
        return
    last_point = points[0]
    last_time = time.time()
    for i in range(1, len(points)):
        x, y = points[i]
        now = time.time()
        dt = now - last_time
        dist = math.hypot(x-last_point[0], y-last_point[1])
        velocity = dist / max(dt, 0.001)
        # Adjust width based on speed
        width = max(1, min(6, 6 - velocity*0.05))
        pygame.draw.aaline(surface, (0,0,0), last_point, (x,y))
        last_point = (x,y)
        last_time = now

# ------------------- MAIN LOOP -------------------
async def run_technipen():
    global running
    client = await connect_device()
    async with client:
        print("Technipen connected!")

        global brush_x, brush_y
        last_time = time.time()

        while running:
            # ------------------- READ IMU -------------------
            x = float((await client.read_gatt_char(CHAR_UUID_X)).decode())
            y = float((await client.read_gatt_char(CHAR_UUID_Y)).decode())
            z = float((await client.read_gatt_char(CHAR_UUID_Z)).decode())  # optional if needed

            # Map IMU to screen coordinates (example mapping)
            # Adjust these scaling factors based on your setup
            raw_x = int(400 + x*50)
            raw_y = int(300 - y*50)
            current_raw.append((raw_x, raw_y))

            if brush_x is None:
                brush_x, brush_y = raw_x, raw_y

            # ------------------- ADAPTIVE SMOOTHING -------------------
            dx = raw_x - brush_x
            dy = raw_y - brush_y
            dist = math.hypot(dx, dy)

            # speed-based smoothing factor: faster movement = higher smoothing (smaller follow)
            dynamic_slow_factor = max(0.05, min(1.0, dist/50))  # tweak scaling
            if dist > radius:
                brush_x += dx * follow
                brush_y += dy * follow
            else:
                brush_x += dx * follow * dynamic_slow_factor
                brush_y += dy * follow * dynamic_slow_factor

            current_smooth.append((brush_x, brush_y))

            # ------------------- PYGAME DRAW -------------------
            screen.fill((255,255,255))

            for stroke in smooth_strokes:
                if len(stroke) > 3:
                    curve = catmull_rom(stroke, 10)
                    draw_stroke(screen, curve)

            if len(current_smooth) > 3:
                curve = catmull_rom(current_smooth, 10)
                draw_stroke(screen, curve)

            pygame.display.flip()
            clock.tick(240)

            # ------------------- EVENT LOOP -------------------
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break

asyncio.run(run_technipen())
pygame.quit()
