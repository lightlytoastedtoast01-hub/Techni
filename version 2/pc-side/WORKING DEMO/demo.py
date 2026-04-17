import pygame
import time
from one_euro import OneEuroFilter

pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

# Smoothing filters
fx = OneEuroFilter(freq=120, min_cutoff=1.0, beta=0.01)
fy = OneEuroFilter(freq=120, min_cutoff=1.0, beta=0.01)

raw_points = []     # unsmoothed
smooth_points = []  # smoothed

running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    if pygame.mouse.get_pressed()[0]:
        raw_x, raw_y = pygame.mouse.get_pos()
        t = time.time()

        # Save raw point
        raw_points.append((raw_x, raw_y))

        # Apply smoothing
        sx = fx(t, raw_x)
        sy = fy(t, raw_y)
        smooth_points.append((sx, sy))

    screen.fill((255, 255, 255))

    # Draw raw path (thin, dotted, red)
    if len(raw_points) > 1:
        for i in range(0, len(raw_points) - 1, 3):  # skip points to make it dotted
            pygame.draw.line(screen, (255, 0, 0), raw_points[i], raw_points[i+1], 1)

    # Draw smoothed path (thick, black)
    if len(smooth_points) > 1:
        pygame.draw.lines(screen, (0, 0, 0), False, smooth_points, 3)

    pygame.display.flip()
    clock.tick(12)  # slow sample rate for testing

pygame.quit()
