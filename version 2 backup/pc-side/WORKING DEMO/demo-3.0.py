import pygame
import time
from one_euro import OneEuroFilter

pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

# OneEuro smoothing filters
fx = OneEuroFilter(freq=240, min_cutoff=0.02, beta=2)
fy = OneEuroFilter(freq=240, min_cutoff=0.02, beta=2)

# Store multiple strokes
raw_strokes = []       # list of lists
smooth_strokes = []    # list of lists

current_raw = []       # active stroke
current_smooth = []    # active stroke

last_draw = 0

running = True
mouse_down = False

alpha = 0.05 # lazy factor

def interpolate(points, steps=5):
    new_points = []

    for i in range(len(points)-1):
        x1,y1 = points[i]
        x2,y2 = points[i+1]

        for s in range(steps):
            t = s/steps
            x = x1 + (x2-x1)*t
            y = y1 + (y2-y1)*t
            new_points.append((x,y))

    new_points.append(points[-1])
    return new_points

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # mouse pressed → start new stroke
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_down = True
            current_raw = []
            current_smooth = []

        # mouse released → finish stroke
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            mouse_down = False
            if current_raw:
                raw_strokes.append(current_raw)
                smooth_strokes.append(current_smooth)

    t = time.time()

    # SAMPLE INPUT
    if mouse_down:
        raw_x, raw_y = pygame.mouse.get_pos()

        # add raw point
        current_raw.append((raw_x, raw_y))

        # strong smoothing
        alpha = 0.03

        if len(current_smooth) == 0:
            sx, sy = raw_x, raw_y
        else:
            px, py = current_smooth[-1]
            sx = px + alpha * (raw_x - px)
            sy = py + alpha * (raw_y - py)

        current_smooth.append((sx, sy))

        last_sample = t

    # DRAW
    if mouse_down:
        screen.fill((255, 255, 255))

        # draw finished raw strokes
        for stroke in raw_strokes:
            for i in range(len(stroke) - 1):
                if i % 3 == 0:
                    pygame.draw.line(screen, (255, 0, 0), stroke[i], stroke[i+1], 1)

        # draw finished smoothed strokes
        for stroke in smooth_strokes:
            if len(stroke) > 1:
                smooth = interpolate(stroke, 6)
                pygame.draw.aalines(screen, (0,0,0), False, smooth)

        # draw active raw stroke
        for i in range(len(current_raw) - 1):
            if i % 3 == 0:
                pygame.draw.line(screen, (255, 0, 0), current_raw[i], current_raw[i+1], 1)

        # draw active smoothed stroke
        if len(current_smooth) > 1:
            pygame.draw.lines(screen, (0, 0, 0), False, current_smooth, 3)

        pygame.display.flip()

    clock.tick(240)

pygame.quit()
