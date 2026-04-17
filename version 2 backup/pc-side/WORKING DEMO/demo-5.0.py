import pygame
import math

pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

raw_strokes = []
smooth_strokes = []

current_raw = []
current_smooth = []

mouse_down = False
running = True

# Lazy brush stabilization
brush_x = None
brush_y = None
radius = 50       # Lazy brush radius
follow = 0.15     # Speed outside radius
slow_factor = 0.25  # Speed factor inside radius


# Catmull-Rom spline
def catmull_rom(points, steps=8):
    if len(points) < 4:
        return points
    curve = []
    for i in range(1, len(points)-2):
        p0 = points[i-1]
        p1 = points[i]
        p2 = points[i+1]
        p3 = points[i+2]
        for j in range(steps):
            t = j / steps
            t2 = t*t
            t3 = t2*t
            x = 0.5 * ((2*p1[0]) + (-p0[0] + p2[0])*t + (2*p0[0]-5*p1[0]+4*p2[0]-p3[0])*t2 + (-p0[0]+3*p1[0]-3*p2[0]+p3[0])*t3)
            y = 0.5 * ((2*p1[1]) + (-p0[1] + p2[1])*t + (2*p0[1]-5*p1[1]+4*p2[1]-p3[1])*t2 + (-p0[1]+3*p1[1]-3*p2[1]+p3[1])*t3)
            curve.append((x, y))
    curve.append(points[-2])
    curve.append(points[-1])
    return curve

# Velocity-based line drawing
def draw_stroke(surface, points):
    if len(points) < 2:
        return
    last_point = points[0]
    last_time = pygame.time.get_ticks() / 1000
    for i in range(1, len(points)):
        x, y = points[i]
        now = pygame.time.get_ticks() / 1000
        dt = now - last_time
        dist = math.hypot(x-last_point[0], y-last_point[1])
        velocity = dist / max(dt, 0.001)
        # slow = thick, fast = thin
        width = max(1, min(6, 6 - velocity*0.05))
        pygame.draw.aaline(surface, (0,0,0), last_point, (x,y))
        last_point = (x,y)
        last_time = now

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_down = True
            current_raw = []
            current_smooth = []
            brush_x, brush_y = None, None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            mouse_down = False
            if current_smooth:
                raw_strokes.append(current_raw)
                smooth_strokes.append(current_smooth)

    if mouse_down:
        raw_x, raw_y = pygame.mouse.get_pos()
        current_raw.append((raw_x, raw_y))

        if brush_x is None:
            brush_x, brush_y = raw_x, raw_y

        dx = raw_x - brush_x
        dy = raw_y - brush_y
        dist = math.hypot(dx, dy)

        # Move brush: slower inside radius, faster outside
        if dist > radius:
            brush_x += dx * follow
            brush_y += dy * follow
        else:
            brush_x += dx * follow * slow_factor
            brush_y += dy * follow * slow_factor

        current_smooth.append((brush_x, brush_y))

    screen.fill((255,255,255))

    # Finished strokes
    for stroke in smooth_strokes:
        if len(stroke) > 3:
            curve = catmull_rom(stroke, 10)
            draw_stroke(screen, curve)

    # Active stroke
    if len(current_smooth) > 3:
        curve = catmull_rom(current_smooth, 10)
        draw_stroke(screen, curve)


    pygame.display.flip()
    clock.tick(240)

pygame.quit()
