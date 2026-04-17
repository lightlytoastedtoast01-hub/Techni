import pygame
import math
import json
import platform
import subprocess
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog
except Exception:
    tk = None
    filedialog = None


pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)

raw_strokes = []
smooth_strokes = []
redo_strokes = []

current_raw = []
current_smooth = []

mouse_down = False
running = True

# === COLOR PALETTE ===
palette = [
    (0,0,0), (255,255,255), (255,0,0), (0,255,0), (0,0,255),
    (255,255,0), (0,255,255), (255,0,255), (128,0,0), (0,128,0),
    (0,0,128), (128,128,0), (0,128,128), (128,0,128), (192,192,192),
    (128,128,128), (255,165,0), (255,105,180), (75,0,130), (0,255,127)
]

current_color = palette[0]
current_stroke_color = current_color
current_brush_size = 6
current_stroke_brush_size = current_brush_size
last_file_path = None
save_button_rect = pygame.Rect(10, 40, 80, 30)
save_as_button_rect = pygame.Rect(100, 40, 100, 30)
load_button_rect = pygame.Rect(210, 40, 80, 30)
undo_button_rect = pygame.Rect(300, 40, 80, 30)
redo_button_rect = pygame.Rect(390, 40, 80, 30)
status_message = "Ready"

# Lazy brush stabilization
brush_x = None
brush_y = None
radius = 50
follow = 0.15
slow_factor = 0.25
debug_shortcuts = True


def debug_log(message):
    if debug_shortcuts:
        print(message, flush=True)


def set_status(message):
    global status_message
    status_message = message
    debug_log(f"[status] {message}")


# Catmull-Rom spline (i got this from google lol)
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

# Draw a stroke with a configurable brush size :D
def draw_stroke(surface, points, color, brush_size):
    if len(points) < 2:
        return
    last_point = points[0]
    for i in range(1, len(points)):
        x, y = points[i]
        pygame.draw.line(surface, color, last_point, (x, y), brush_size)
        pygame.draw.circle(surface, color, (int(x), int(y)), max(1, brush_size // 2))
        last_point = (x, y)


def prompt_file_path_tk(save_dialog):
    if tk is None or filedialog is None:
        return None

    root = tk.Tk()
    root.withdraw()
    if hasattr(root, "attributes"):
        root.attributes("-topmost", True)
    filetypes = [("TechniPen files", "*.tpn")]
    default_name = "drawing.tpn"
    try:
        if save_dialog:
            path = filedialog.asksaveasfilename(
                defaultextension=".tpn",
                filetypes=filetypes,
                initialfile=default_name
            )
        else:
            path = filedialog.askopenfilename(filetypes=filetypes)
    finally:
        root.destroy()
    return Path(path) if path else None


def run_osascript(script_lines):
    try:
        result = subprocess.run(
            ["osascript", *sum([["-e", line] for line in script_lines], [])],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError:
        return None

    output = result.stdout.strip()
    return Path(output) if output else None


def prompt_file_path_macos(save_dialog):
    if save_dialog:
        chosen_path = run_osascript([
            'set chosenFile to choose file name with prompt "Save TechniPen drawing" default name "drawing.tpn"',
            'POSIX path of chosenFile'
        ])
        if chosen_path is not None and chosen_path.suffix.lower() != ".tpn":
            chosen_path = chosen_path.with_suffix(".tpn")
        return chosen_path

    return run_osascript([
        'set chosenFile to choose file with prompt "Load TechniPen drawing"',
        'POSIX path of chosenFile'
    ])


def prompt_file_path(save_dialog):
    if platform.system() == "Darwin":
        return prompt_file_path_macos(save_dialog)
    return prompt_file_path_tk(save_dialog)


def serialize_stroke_list(stroke_list):
    return [
        {
            "points": [[float(x), float(y)] for x, y in stroke],
            "color": list(color),
            "brush_size": brush_size
        }
        for stroke, color, brush_size in stroke_list
    ]


def deserialize_stroke_list(entries):
    strokes = []
    for entry in entries:
        points = [tuple(point) for point in entry.get("points", [])]
        color = tuple(entry.get("color", [0, 0, 0]))
        brush_size = int(entry.get("brush_size", 6))
        if points:
            strokes.append((points, color, max(1, min(40, brush_size))))
    return strokes


def save_drawing(path):
    debug_log(f"[save] Saving {len(smooth_strokes)} strokes and {len(redo_strokes)} redo strokes to {path}")
    data = {
        "format": "TechniPen",
        "version": 2,
        "strokes": serialize_stroke_list(smooth_strokes),
        "redo_strokes": serialize_stroke_list(redo_strokes)
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    set_status(f"Saved {path.name}")


def load_drawing(path):
    global smooth_strokes, raw_strokes, current_raw, current_smooth, redo_strokes
    global mouse_down, brush_x, brush_y

    data = json.loads(path.read_text(encoding="utf-8"))
    smooth_strokes = deserialize_stroke_list(data.get("strokes", []))
    redo_strokes = deserialize_stroke_list(data.get("redo_strokes", []))
    raw_strokes = []
    current_raw = []
    current_smooth = []
    mouse_down = False
    brush_x = None
    brush_y = None
    debug_log(f"[load] Loaded {len(smooth_strokes)} strokes and {len(redo_strokes)} redo strokes from {path}")
    set_status(f"Loaded {path.name}")


def open_save_dialog():
    global last_file_path
    debug_log("[save] Opening save dialog")
    chosen_path = last_file_path or prompt_file_path(save_dialog=True)
    if chosen_path is not None:
        save_drawing(chosen_path)
        last_file_path = chosen_path
        debug_log(f"[save] Current file set to {last_file_path}")
    else:
        debug_log("[save] Save dialog cancelled")
        set_status("Save cancelled")


def open_save_as_dialog():
    global last_file_path
    debug_log("[save_as] Opening save as dialog")
    chosen_path = prompt_file_path(save_dialog=True)
    if chosen_path is not None:
        save_drawing(chosen_path)
        last_file_path = chosen_path
        debug_log(f"[save_as] Current file set to {last_file_path}")
    else:
        debug_log("[save_as] Save as dialog cancelled")
        set_status("Save As cancelled")


def open_load_dialog():
    global last_file_path
    debug_log("[load] Opening load dialog")
    chosen_path = prompt_file_path(save_dialog=False)
    if chosen_path is not None:
        load_drawing(chosen_path)
        last_file_path = chosen_path
        debug_log(f"[load] Current file set to {last_file_path}")
    else:
        debug_log("[load] Load dialog cancelled")
        set_status("Load cancelled")


def draw_button(surface, rect, label):
    pygame.draw.rect(surface, (235, 235, 235), rect, border_radius=6)
    pygame.draw.rect(surface, (40, 40, 40), rect, 2, border_radius=6)
    text = font.render(label, True, (0, 0, 0))
    text_rect = text.get_rect(center=rect.center)
    surface.blit(text, text_rect)


def undo_stroke():
    debug_log(f"[undo] Attempting undo. strokes={len(smooth_strokes)} redo={len(redo_strokes)}")
    if smooth_strokes:
        redo_strokes.append(smooth_strokes.pop())
        debug_log(f"[undo] Success. strokes={len(smooth_strokes)} redo={len(redo_strokes)}")
        set_status("Undo")
    else:
        debug_log("[undo] Nothing to undo")
        set_status("Nothing to undo")


def redo_stroke():
    debug_log(f"[redo] Attempting redo. strokes={len(smooth_strokes)} redo={len(redo_strokes)}")
    if redo_strokes:
        smooth_strokes.append(redo_strokes.pop())
        debug_log(f"[redo] Success. strokes={len(smooth_strokes)} redo={len(redo_strokes)}")
        set_status("Redo")
    else:
        debug_log("[redo] Nothing to redo")
        set_status("Nothing to redo")

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # === COLOR KEYBINDS (20 COLORS) ===
        if event.type == pygame.KEYDOWN:
            mods = getattr(event, "mod", 0)
            shortcut_mod = mods & (pygame.KMOD_CTRL | pygame.KMOD_META)
            debug_log(
                f"[key] key={pygame.key.name(event.key)} unicode={repr(getattr(event, 'unicode', ''))} "
                f"mods={mods} ctrl={bool(mods & pygame.KMOD_CTRL)} meta={bool(mods & pygame.KMOD_META)}"
            )
            keys = [
                pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5,
                pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9, pygame.K_0,
                pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r, pygame.K_t,
                pygame.K_y, pygame.K_u, pygame.K_i, pygame.K_o, pygame.K_p
            ]
            if shortcut_mod and event.key == pygame.K_s:
                debug_log("[key] Save shortcut detected")
                if mods & pygame.KMOD_SHIFT:
                    open_save_as_dialog()
                else:
                    open_save_dialog()
            elif shortcut_mod and event.key == pygame.K_o:
                debug_log("[key] Load shortcut detected")
                open_load_dialog()
            elif shortcut_mod and event.key == pygame.K_z:
                debug_log("[key] Undo shortcut detected")
                undo_stroke()
            elif shortcut_mod and event.key == pygame.K_x:
                debug_log("[key] Redo shortcut detected")
                redo_stroke()
            elif event.key in keys:
                current_color = palette[keys.index(event.key)]
                debug_log(f"[color] Selected palette index {keys.index(event.key)} color={current_color}")
            elif event.key in (pygame.K_LEFTBRACKET, pygame.K_MINUS):
                current_brush_size = max(1, current_brush_size - 1)
                debug_log(f"[brush] Decreased size to {current_brush_size}")
            elif event.key in (pygame.K_RIGHTBRACKET, pygame.K_EQUALS):
                current_brush_size = min(40, current_brush_size + 1)
                debug_log(f"[brush] Increased size to {current_brush_size}")

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if save_button_rect.collidepoint(event.pos):
                debug_log("[mouse] Save button clicked")
                open_save_dialog()
                continue
            if save_as_button_rect.collidepoint(event.pos):
                debug_log("[mouse] Save As button clicked")
                open_save_as_dialog()
                continue
            if load_button_rect.collidepoint(event.pos):
                debug_log("[mouse] Load button clicked")
                open_load_dialog()
                continue
            if undo_button_rect.collidepoint(event.pos):
                debug_log("[mouse] Undo button clicked")
                undo_stroke()
                continue
            if redo_button_rect.collidepoint(event.pos):
                debug_log("[mouse] Redo button clicked")
                redo_stroke()
                continue
            mouse_down = True
            current_raw = []
            current_smooth = []
            brush_x, brush_y = None, None
            current_stroke_color = current_color[:]   # locks color
            current_stroke_brush_size = current_brush_size
            debug_log(f"[stroke] Started stroke color={current_stroke_color} size={current_stroke_brush_size}")
            set_status("Drawing")

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            mouse_down = False
            if current_smooth:
                raw_strokes.append((current_raw, current_color))
                smooth_strokes.append((current_smooth[:], current_stroke_color, current_stroke_brush_size))
                redo_strokes.clear()
                debug_log(
                    f"[stroke] Finished stroke points={len(current_smooth)} "
                    f"total={len(smooth_strokes)} redo_cleared={len(redo_strokes)}"
                )
                set_status(f"Stroke count: {len(smooth_strokes)}")
            current_raw = []
            current_smooth = []
            brush_x, brush_y = None, None

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
    for stroke, color, brush_size in smooth_strokes:
        if len(stroke) > 3:
            curve = catmull_rom(stroke, 10)
            draw_stroke(screen, curve, color, brush_size)

    # Active stroke
    if len(current_smooth) > 3:
        curve = catmull_rom(current_smooth, 10)
        draw_stroke(screen, curve, current_stroke_color, current_stroke_brush_size)

    margin = 10
    preview_center = (margin + 20, margin + 20)
    pygame.draw.circle(screen, current_color, preview_center, max(1, current_brush_size // 2))
    pygame.draw.circle(screen, (0,0,0), preview_center, max(1, current_brush_size // 2), 1)
    size_text = font.render(f"Size: {current_brush_size}", True, (0, 0, 0))
    screen.blit(size_text, (margin + 45, margin + 10))
    draw_button(screen, save_button_rect, "Save")
    draw_button(screen, save_as_button_rect, "Save As")
    draw_button(screen, load_button_rect, "Load")
    draw_button(screen, undo_button_rect, "Undo")
    draw_button(screen, redo_button_rect, "Redo")

    if last_file_path is not None:
        file_text = font.render(last_file_path.name, True, (0, 0, 0))
        screen.blit(file_text, (margin, margin + 80))

    status_text = font.render(status_message, True, (0, 0, 0))
    screen.blit(status_text, (margin, margin + 110))

    pygame.display.flip()
    clock.tick(240)

pygame.quit()
# bleugh
# 430 lines .-.
