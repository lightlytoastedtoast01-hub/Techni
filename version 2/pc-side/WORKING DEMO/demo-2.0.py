import pygame
import time
from one_euro import OneEuroFilter

pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

# OneEuro smoothing filters
fx = OneEuroFilter(freq=120, min_cutoff=1.0, beta=1000) # og for both is 0.01
fy = OneEuroFilter(freq=120, min_cutoff=1.0, beta=1000)

# Store multiple strokes
raw_strokes = []       # list of lists
smooth_strokes = []    # list of lists

current_raw = []       # active stroke
current_smooth = []    # active stroke

# sampling + drawing intervals
last_sample = 0
sample_interval = 0.01   # 100 Hz sampling aka 0.01

last_draw = 0
draw_interval = 0.05     # 20 FPS drawing aka 0.05

running = True
mouse_down = False

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
        if t - last_sample >= sample_interval:
            raw_x, raw_y = pygame.mouse.get_pos()

            # add raw point
            current_raw.append((raw_x, raw_y))

            # smooth
            sx = fx(t, raw_x)
            sy = fy(t, raw_y)
            current_smooth.append((sx, sy))

            last_sample = t

    # DRAW
    if t - last_draw >= draw_interval:
        screen.fill((255, 255, 255))

        # draw finished raw strokes
        for stroke in raw_strokes:
            for i in range(len(stroke) - 1):
                if i % 3 == 0:
                    pygame.draw.line(screen, (255, 0, 0), stroke[i], stroke[i+1], 1)

        # draw finished smoothed strokes
        for stroke in smooth_strokes:
            if len(stroke) > 1:
                pygame.draw.lines(screen, (0, 0, 0), False, stroke, 3)

        # draw active raw stroke
        for i in range(len(current_raw) - 1):
            if i % 3 == 0:
                pygame.draw.line(screen, (255, 0, 0), current_raw[i], current_raw[i+1], 1)

        # draw active smoothed stroke
        if len(current_smooth) > 1:
            pygame.draw.lines(screen, (0, 0, 0), False, current_smooth, 3)

        pygame.display.flip()
        last_draw = t

    clock.tick(240)

pygame.quit()
