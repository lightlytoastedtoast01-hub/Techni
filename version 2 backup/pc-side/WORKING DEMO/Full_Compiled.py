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

# === COLOR PALETTE (20 COLORS) ===
palette = [
    (0,0,0), (255,255,255), (255,0,0), (0,255,0), (0,0,255),
    (255,255,0), (0,255,255), (255,0,255), (128,0,0), (0,128,0),
    (0,0,128), (128,128,0), (0,128,128), (128,0,128), (192,192,192),
    (128,128,128), (255,165,0), (255,105,180), (75,0,130), (0,255,127)
]

current_color = palette[0]
current_stroke_color = current_color

# Lazy brush stabilization
brush_x = None
brush_y = None
radius = 50
follow = 0.15
slow_factor = 0.25


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
def draw_stroke(surface, points, color):
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
        width = max(1, min(6, 6 - velocity*0.05))
        pygame.draw.aaline(surface, color, last_point, (x,y))
        last_point = (x,y)
        last_time = now

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # === COLOR KEYBINDS (20 COLORS) ===
        if event.type == pygame.KEYDOWN:
            keys = [
                pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5,
                pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9, pygame.K_0,
                pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r, pygame.K_t,
                pygame.K_y, pygame.K_u, pygame.K_i, pygame.K_o, pygame.K_p
            ]
            if event.key in keys:
                current_color = palette[keys.index(event.key)]

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_down = True
            current_raw = []
            current_smooth = []
            brush_x, brush_y = None, None
            current_stroke_color = current_color[:]   # locks color

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            mouse_down = False
            if current_smooth:
                raw_strokes.append((current_raw, current_color))
                smooth_strokes.append((current_smooth, current_stroke_color))

    if mouse_down:
        raw_x, raw_y = pygame.mouse.get_pos()
        current_raw.append((raw_x, raw_y))

        if brush_x is None:
            brush_x, brush_y = raw_x, raw_y

        dx = raw_x - brush_x
        dy = raw_y - brush_y
        dist = math.hypot(dx, dy)

        if dist > radius:
            brush_x += dx * follow
            brush_y += dy * follow
        else:
            brush_x += dx * follow * slow_factor
            brush_y += dy * follow * slow_factor

        current_smooth.append((brush_x, brush_y))

    screen.fill((255,255,255))

    # Finished strokes
    for stroke, color in smooth_strokes:
        if len(stroke) > 3:
            curve = catmull_rom(stroke, 10)
            draw_stroke(screen, curve, color)

    # Active stroke
    if len(current_smooth) > 3:
        curve = catmull_rom(current_smooth, 10)
        draw_stroke(screen, curve, current_stroke_color)


    # === COLOR INDICATOR :D ===
    indicator_size = 30
    margin = 10
    rect = pygame.Rect(
        screen.get_width() - indicator_size - margin,
        margin,
        indicator_size,
        indicator_size
    )
    pygame.draw.rect(screen, current_color, rect)
    pygame.draw.rect(screen, (0,0,0), rect, 2)  # border

    pygame.display.flip()
    clock.tick(240)

pygame.quit()