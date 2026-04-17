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

# Stabilizer
brush_x = None
brush_y = None
radius = 50
follow = 0.15


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

            x = 0.5 * (
                (2*p1[0]) +
                (-p0[0] + p2[0]) * t +
                (2*p0[0] - 5*p1[0] + 4*p2[0] - p3[0]) * t2 +
                (-p0[0] + 3*p1[0] - 3*p2[0] + p3[0]) * t3
            )

            y = 0.5 * (
                (2*p1[1]) +
                (-p0[1] + p2[1]) * t +
                (2*p0[1] - 5*p1[1] + 4*p2[1] - p3[1]) * t2 +
                (-p0[1] + 3*p1[1] - 3*p2[1] + p3[1]) * t3
            )

            curve.append((x, y))

    curve.append(points[-2])
    curve.append(points[-1])
    return curve


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
        dist = math.sqrt(dx*dx + dy*dy)

        if dist > radius:
            brush_x += dx * follow
            brush_y += dy * follow

        current_smooth.append((brush_x, brush_y))

    screen.fill((255,255,255))

    # finished strokes
    for stroke in smooth_strokes:
        if len(stroke) > 3:
            curve = catmull_rom(stroke, 10)
            pygame.draw.aalines(screen, (0,0,0), False, curve)

    # active stroke
    if len(current_smooth) > 3:
        curve = catmull_rom(current_smooth, 10)
        pygame.draw.aalines(screen, (0,0,0), False, curve)

    pygame.display.flip()
    clock.tick(240)

pygame.quit()
