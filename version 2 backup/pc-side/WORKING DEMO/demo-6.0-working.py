import asyncio
from bleak import BleakScanner, BleakClient
import pygame
import time

# ------------------- BLE SETTINGS -------------------
BLE_MAC = "f2:4f:18:a6:f7:76"
DEVICE_NAME = "Arduino"
CHAR_UUID = "19B10004-E8F2-537E-4F6C-D104768A1214"  # X,Y,Z as bytes

# ------------------- PYGAME SETTINGS -------------------
pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

running = True
brush_x = None
brush_y = None
radius = 20      # Actual lazy pen radius
follow = 0.15
slow_factor = 0.25

raw_strokes = []
smooth_strokes = []
current_raw = []
current_smooth = []

last_pen_x = 0
last_pen_y = 0
latest_pen = {"x": 0.0, "y": 0.0, "z": 0.0}

SCALE = 8  # IMU → screen pixels

# ------------------- CATMULL-ROM -------------------
def catmull_rom(points, steps=8):
    if len(points) < 4: return points
    curve = []
    for i in range(1, len(points)-2):
        p0,p1,p2,p3 = points[i-1], points[i], points[i+1], points[i+2]
        for j in range(steps):
            t = j/steps
            t2, t3 = t*t, t*t*t
            x = 0.5*((2*p1[0]) + (-p0[0]+p2[0])*t + (2*p0[0]-5*p1[0]+4*p2[0]-p3[0])*t2 + (-p0[0]+3*p1[0]-3*p2[0]+p3[0])*t3)
            y = 0.5*((2*p1[1]) + (-p0[1]+p2[1])*t + (2*p0[1]-5*p1[1]+4*p2[1]-p3[1])*t2 + (-p0[1]+3*p1[1]-3*p2[1]+p3[1])*t3)
            curve.append((x, y))
    curve.append(points[-2])
    curve.append(points[-1])
    return curve

def draw_stroke(surface, points):
    if len(points)<2: return
    last = points[0]
    for pt in points[1:]:
        pygame.draw.aaline(surface,(0,0,0),last,pt)
        last = pt

# ------------------- BLE HANDLER -------------------
async def ble_loop():
    global latest_pen
    try:
        client = BleakClient(BLE_MAC)
        await client.connect()
        if client.is_connected:
            print("Connected via MAC")
    except Exception as e:
        print("MAC failed:", e)
        devices = await BleakScanner.discover()
        client = None
        for d in devices:
            if d.name == DEVICE_NAME:
                client = BleakClient(d.address)
                await client.connect()
                print("Connected via Name")
                break
        if client is None:
            raise Exception("Device not found")

    def handle_notify(sender, data: bytearray):
        import struct
        x, y, z = struct.unpack('fff', data)
        latest_pen["x"] = x
        latest_pen["y"] = y
        latest_pen["z"] = z

    await client.start_notify(CHAR_UUID, handle_notify)

    while running:
        await asyncio.sleep(0.01)

# ------------------- MAIN LOOP -------------------
async def run_technipen():
    global running, brush_x, brush_y, last_pen_x, last_pen_y

    ble_task = asyncio.create_task(ble_loop())

    while running:
        raw_x, raw_y = pygame.mouse.get_pos()
        current_raw.append((raw_x, raw_y))

        # ----- PEN SPEED -----
        pen_x = latest_pen["x"]
        pen_y = latest_pen["y"]
        dx_pen = pen_x - last_pen_x
        dy_pen = pen_y - last_pen_y
        pen_speed = abs(dx_pen) + abs(dy_pen)
        last_pen_x = pen_x
        last_pen_y = pen_y

        # ----- LAZY PEN + SPEED SMOOTHING -----
        dx = raw_x - (brush_x if brush_x is not None else raw_x)
        dy = raw_y - (brush_y if brush_y is not None else raw_y)
        dist = abs(dx) + abs(dy)
        beta = min(0.95, 0.05 + pen_speed*0.02)

        if brush_x is None:
            brush_x, brush_y = raw_x, raw_y

        if dist > radius:
            brush_x += dx * follow * beta
            brush_y += dy * follow * beta
        else:
            brush_x += dx * follow * slow_factor * beta
            brush_y += dy * follow * slow_factor * beta

        current_smooth.append((brush_x, brush_y))

        # ----- DRAW -----
        screen.fill((255,255,255))
        for stroke in smooth_strokes:
            if len(stroke)>3:
                curve = catmull_rom(stroke,10)
                draw_stroke(screen,curve)
        if len(current_smooth)>3:
            curve = catmull_rom(current_smooth,10)
            draw_stroke(screen,curve)
        pygame.display.flip()
        clock.tick(240)

        # ----- EVENTS -----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                current_raw.clear()
                current_smooth.clear()
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                raw_strokes.append(list(current_raw))
                smooth_strokes.append(list(current_smooth))
                current_raw.clear()
                current_smooth.clear()

    await ble_task

asyncio.run(run_technipen())
pygame.quit()
