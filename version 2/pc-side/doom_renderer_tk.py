import json
from collections import deque
import math
import random
import time
import tkinter as tk


MAP_LAYOUT = [
    "################",
    "#..............#",
    "#..##..........#",
    "#..............#",
    "#......####....#",
    "#..............#",
    "#....##........#",
    "#...........#..#",
    "#..............#",
    "################",
]

TILE_SIZE = 1.0
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 600
HALF_HEIGHT = SCREEN_HEIGHT // 2
FOV = math.radians(66)
NUM_RAYS = 240
MAX_DEPTH = 20
MOVE_SPEED = 3.2
MOVE_ACCEL = 14.0
MOVE_DECEL = 16.0
TURN_SPEED = math.radians(130)
TURN_ACCEL = math.radians(720)
TURN_DECEL = math.radians(840)
MINIMAP_SCALE = 14
MINIMAP_RADIUS_TILES = 3
ZOMBIE_RADIUS = 0.22
PLAYER_RADIUS = 0.18
PLAYER_MAX_HP = 100
ZOMBIE_ATTACK_RANGE = 0.45
ZOMBIE_ATTACK_COOLDOWN = 0.7
SHOT_COOLDOWN = 0.28
SPAWN_INTERVAL = 5.0
LOOT_DROP_CHANCE = 0.50
LOOT_PICKUP_RANGE = 0.72
FOOD_HEAL = 28
RELOAD_KEY = "r"
INVENTORY_KEY = "e"
MAP_KEY = "m"
INVENTORY_SLOTS = 18
INVENTORY_COLS = 6
INVENTORY_ROWS = 3
SLOT_SIZE = 84
SLOT_GAP = 12
SAVE_FILE = "savegame.dpy"
MAX_LIVING_ZOMBIES = 5
PLAYER_SPAWN_BUFFER = 3.0
ZOMBIE_SPAWN_BUFFER = 1.0
MAX_RESERVE_AMMO = 200
LEVEL_KILL_TARGET = 20
MAP_SIZES = (
    ("small", 16, 10),
    ("medium", 32, 20),
    ("large", 64, 40),
)
SPAWN_POINTS = [
    (8.5, 2.5),
    (11.5, 7.5),
    (6.5, 7.5),
    (13.5, 2.5),
    (2.5, 7.5),
    (10.5, 4.5),
]
ZOMBIE_TYPES = (
    {"name": "walker", "speed": 1.00, "hp": 45, "damage": 18, "color_bias": (0, 0, 0)},
    {"name": "runner", "speed": 1.65, "hp": 30, "damage": 12, "color_bias": (18, 18, -12)},
    {"name": "brute", "speed": 0.72, "hp": 70, "damage": 28, "color_bias": (22, -10, -10)},
)
GUNS = [
    {"name": "Knife", "damage": 16, "cooldown": 0.38, "color": "#d8d8d8", "magazine": 1, "ammo_drop": 0, "reload_time": 0.0, "craft_cost": 0, "melee": True, "range": 1.25},
    {"name": "Pistol", "damage": 25, "cooldown": 0.28, "color": "#9ba4b4", "magazine": 10, "ammo_drop": 18, "reload_time": 1.2, "craft_cost": 8},
    {"name": "Repeater", "damage": 34, "cooldown": 0.22, "color": "#c9d46a", "magazine": 14, "ammo_drop": 24, "reload_time": 1.45, "craft_cost": 16},
    {"name": "Scattergun", "damage": 48, "cooldown": 0.34, "color": "#ff9866", "magazine": 6, "ammo_drop": 10, "reload_time": 1.6, "craft_cost": 30},
    {"name": "Burst Rifle", "damage": 28, "cooldown": 0.16, "color": "#7fc8ff", "magazine": 18, "ammo_drop": 26, "reload_time": 1.35, "craft_cost": 42},
    {"name": "Heavy Cannon", "damage": 62, "cooldown": 0.52, "color": "#ff9b7d", "magazine": 5, "ammo_drop": 8, "reload_time": 1.85, "craft_cost": 60},
]
LOOT_TYPES = (
    {"type": "ammo", "weight": 40},
    {"type": "food", "weight": 30},
    {"type": "materials", "weight": 30},
)


def clamp(value, low, high):
    return max(low, min(high, value))


def rgb(r, g, b):
    return f"#{clamp(int(r), 0, 255):02x}{clamp(int(g), 0, 255):02x}{clamp(int(b), 0, 255):02x}"


class RaycasterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TechniPen Survival")
        self.canvas = tk.Canvas(
            root,
            width=SCREEN_WIDTH,
            height=SCREEN_HEIGHT,
            bg="#0b0b0b",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.root.minsize(640, 400)

        self.player_x = 3.5
        self.player_y = 3.5
        self.player_angle = 0.0
        self.move_velocity_x = 0.0
        self.move_velocity_y = 0.0
        self.turn_velocity = 0.0
        self.player_hp = PLAYER_MAX_HP
        self.gun_index = 0
        self.reserve_ammo = GUNS[1]["magazine"] * 6
        self.mag_ammo = 1
        self.keys = set()
        self.wall_depths = [MAX_DEPTH] * NUM_RAYS
        self.zombies = []
        self.loot_boxes = []
        self.collected_loot_ids = set()
        self.next_loot_id = 1
        self.inventory = [None for _ in range(INVENTORY_SLOTS)]
        self.inventory_open = False
        self.pause_menu_open = False
        self.map_view_open = False
        self.selected_slot = None
        self.drag_item = None
        self.drag_origin = None
        self.mouse_x = 0
        self.mouse_y = 0
        self.inventory_buttons = {}
        self.pause_buttons = {}
        self.death_buttons = {}
        self.last_shot_time = 0.0
        self.muzzle_flash = 0.0
        self.game_over = False
        self.reload_timer = 0.0
        self.spawn_index = 0
        self.spawn_timer = SPAWN_INTERVAL
        self.level_index = 1
        self.kill_count = 0
        self.map_size_name = "small"
        self.message = ""
        self.message_timer = 0.0
        self.last_time = time.perf_counter()
        self.map_layout = list(MAP_LAYOUT)
        self.generate_new_level(initial=True)

        root.bind("<KeyPress>", self.on_key_press)
        root.bind("<KeyRelease>", self.on_key_release)
        root.bind("<Escape>", self.on_escape)
        root.bind("<Configure>", self.on_resize)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.focus_set()
        self.loop()

    def on_key_press(self, event):
        key = event.keysym.lower()
        self.keys.add(key)
        if key == INVENTORY_KEY:
            if self.pause_menu_open or self.map_view_open:
                return
            self.toggle_inventory()
            return
        if key == MAP_KEY:
            if self.inventory_open:
                return
            self.toggle_map_view()
            return
        if self.inventory_open or self.pause_menu_open or self.map_view_open:
            return
        if key == "space":
            self.fire_weapon()
        if key == RELOAD_KEY:
            self.start_reload()

    def on_key_release(self, event):
        self.keys.discard(event.keysym.lower())

    def on_resize(self, event):
        global SCREEN_WIDTH, SCREEN_HEIGHT, HALF_HEIGHT
        if event.widget is not self.root:
            return
        new_width = max(640, int(event.width))
        new_height = max(400, int(event.height))
        if new_width == SCREEN_WIDTH and new_height == SCREEN_HEIGHT:
            return
        SCREEN_WIDTH = new_width
        SCREEN_HEIGHT = new_height
        HALF_HEIGHT = SCREEN_HEIGHT // 2
        self.canvas.config(width=SCREEN_WIDTH, height=SCREEN_HEIGHT)

    def on_mouse_move(self, event):
        self.mouse_x = event.x
        self.mouse_y = event.y

    def on_mouse_down(self, event):
        if not self.inventory_open:
            return

        self.mouse_x = event.x
        self.mouse_y = event.y
        eq_x0, eq_y0, eq_x1, eq_y1 = self.equipment_slot_rect()
        if eq_x0 <= event.x <= eq_x1 and eq_y0 <= event.y <= eq_y1:
            return
        slot_index = self.inventory_slot_at(event.x, event.y)
        if slot_index is None:
            return

        self.selected_slot = slot_index
        if self.inventory[slot_index] is not None:
            self.drag_item = self.inventory[slot_index]
            self.inventory[slot_index] = None
            self.drag_origin = slot_index

    def on_mouse_up(self, event):
        if self.game_over:
            self.mouse_x = event.x
            self.mouse_y = event.y
            for action, rect in self.death_buttons.items():
                x0, y0, x1, y1 = rect
                if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                    self.handle_death_action(action)
                    return
            return

        if self.pause_menu_open:
            self.mouse_x = event.x
            self.mouse_y = event.y
            for action, rect in self.pause_buttons.items():
                x0, y0, x1, y1 = rect
                if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                    self.handle_pause_action(action)
                    return
            return

        if not self.inventory_open:
            return

        self.mouse_x = event.x
        self.mouse_y = event.y

        if self.drag_item is not None:
            eq_x0, eq_y0, eq_x1, eq_y1 = self.equipment_slot_rect()
            if eq_x0 <= event.x <= eq_x1 and eq_y0 <= event.y <= eq_y1:
                if self.drag_item["type"] == "gun":
                    self.equip_gun_to_slot(self.drag_item["gun_index"], self.drag_origin)
                else:
                    self.inventory[self.drag_origin] = self.drag_item
                self.drag_item = None
                self.drag_origin = None
                return
            slot_index = self.inventory_slot_at(event.x, event.y)
            if slot_index is None:
                self.inventory[self.drag_origin] = self.drag_item
            else:
                self.inventory[slot_index], self.drag_item = self.drag_item, self.inventory[slot_index]
                if self.drag_item is not None:
                    self.inventory[self.drag_origin] = self.drag_item
                self.selected_slot = slot_index
            self.drag_item = None
            self.drag_origin = None
            return

        for action, rect in self.inventory_buttons.items():
            x0, y0, x1, y1 = rect
            if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                self.handle_inventory_action(action)
                return

    def on_escape(self, _event):
        if self.inventory_open:
            self.toggle_inventory(force=False)
            return
        if self.map_view_open:
            self.toggle_map_view(False)
            return
        if self.game_over:
            self.root.destroy()
            return
        self.toggle_pause_menu()

    def is_wall(self, x, y):
        map_x = int(x // TILE_SIZE)
        map_y = int(y // TILE_SIZE)
        if map_y < 0 or map_y >= len(self.map_layout):
            return True
        if map_x < 0 or map_x >= len(self.map_layout[0]):
            return True
        return self.map_layout[map_y][map_x] == "#"

    def try_move(self, next_x, next_y):
        padding = PLAYER_RADIUS
        if not self.is_wall(next_x + padding, self.player_y) and not self.is_wall(
            next_x - padding, self.player_y
        ):
            self.player_x = next_x
        if not self.is_wall(self.player_x, next_y + padding) and not self.is_wall(
            self.player_x, next_y - padding
        ):
            self.player_y = next_y

    def is_position_blocked(self, x, y, radius):
        return (
            self.is_wall(x + radius, y)
            or self.is_wall(x - radius, y)
            or self.is_wall(x, y + radius)
            or self.is_wall(x, y - radius)
        )

    def can_spawn_at(self, x, y, radius):
        if self.is_position_blocked(x, y, radius):
            return False
        if self.is_wall(x, y):
            return False
        if math.hypot(x - self.player_x, y - self.player_y) < PLAYER_SPAWN_BUFFER:
            return False
        if any(
            zombie["alive"] and math.hypot(x - zombie["x"], y - zombie["y"]) < ZOMBIE_SPAWN_BUFFER
            for zombie in self.zombies
        ):
            return False
        return True

    def map_floor_positions(self):
        positions = []
        for y, row in enumerate(self.map_layout):
            for x, tile in enumerate(row):
                if tile != "#":
                    positions.append((x + 0.5, y + 0.5))
        return positions

    def rebuild_spawn_points(self):
        candidate_points = []
        for x, y in self.map_floor_positions():
            if 1.5 <= x <= len(self.map_layout[0]) - 1.5 and 1.5 <= y <= len(self.map_layout) - 1.5:
                if not self.is_position_blocked(x, y, ZOMBIE_RADIUS):
                    candidate_points.append((x, y))
        self.spawn_points = candidate_points if candidate_points else list(SPAWN_POINTS)

    def safe_player_spawn(self):
        floor_positions = self.map_floor_positions()
        if not floor_positions:
            return 1.5, 1.5

        center_x = len(self.map_layout[0]) / 2
        center_y = len(self.map_layout) / 2
        floor_positions.sort(key=lambda pos: math.hypot(pos[0] - center_x, pos[1] - center_y))
        for x, y in floor_positions:
            if not self.is_position_blocked(x, y, PLAYER_RADIUS):
                return x, y
        return floor_positions[0]

    def corner_coverage_ok(self, spawn_x, spawn_y):
        start = (int(spawn_x), int(spawn_y))
        visited = {start}
        queue = deque([start])
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]

        while queue:
            x, y = queue.popleft()
            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                if (nx, ny) in visited:
                    continue
                if ny < 0 or ny >= len(self.map_layout) or nx < 0 or nx >= len(self.map_layout[0]):
                    continue
                if self.map_layout[ny][nx] == "#":
                    continue
                visited.add((nx, ny))
                queue.append((nx, ny))

        corners = [
            (0, 0),
            (len(self.map_layout[0]) - 1, 0),
            (0, len(self.map_layout) - 1),
            (len(self.map_layout[0]) - 1, len(self.map_layout) - 1),
        ]
        for corner_x, corner_y in corners:
            found = False
            for y in range(len(self.map_layout)):
                for x in range(len(self.map_layout[0])):
                    if (x, y) not in visited:
                        continue
                    if math.hypot(x - corner_x, y - corner_y) <= 5.0:
                        found = True
                        break
                if found:
                    break
            if not found:
                return False
        return True

    def choose_map_size(self):
        choices = [entry for entry in MAP_SIZES if entry[0] != self.map_size_name]
        if not choices:
            choices = list(MAP_SIZES)
        return random.choice(choices)

    def generate_procedural_map(self, width, height):
        grid = [["#" for _ in range(width)] for _ in range(height)]
        carved_rooms = []

        room_x = random.randint(1, 3)
        room_y = random.randint(1, 2)
        room_w = random.randint(4, 6)
        room_h = random.randint(3, 4)
        for y in range(room_y, room_y + room_h):
            for x in range(room_x, room_x + room_w):
                grid[y][x] = "."
        carved_rooms.append((room_x, room_y, room_w, room_h))

        current_x = room_x + room_w // 2
        current_y = room_y + room_h // 2
        branch_count = max(7, (width * height) // 45)
        for _ in range(branch_count):
            direction = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
            length = random.randint(2, max(5, min(width, height) // 3))
            corridor = []
            nx, ny = current_x, current_y
            for _ in range(length):
                nx = clamp(nx + direction[0], 1, width - 2)
                ny = clamp(ny + direction[1], 1, height - 2)
                corridor.append((nx, ny))
            for cx, cy in corridor:
                grid[cy][cx] = "."

            room_w = random.randint(3, max(5, width // 7))
            room_h = random.randint(3, max(4, height // 7))
            room_x = clamp(nx - room_w // 2, 1, width - room_w - 1)
            room_y = clamp(ny - room_h // 2, 1, height - room_h - 1)
            for y in range(room_y, room_y + room_h):
                for x in range(room_x, room_x + room_w):
                    grid[y][x] = "."
            carved_rooms.append((room_x, room_y, room_w, room_h))
            current_x = nx
            current_y = ny

        for room_x, room_y, room_w, room_h in carved_rooms:
            if room_w < 4 or room_h < 4:
                continue

            pillar_attempts = max(1, (room_w * room_h) // 18)
            for _ in range(pillar_attempts):
                if random.random() < 0.65:
                    px = random.randint(room_x + 1, room_x + room_w - 2)
                    py = random.randint(room_y + 1, room_y + room_h - 2)
                    if abs(px - (room_x + room_w // 2)) <= 1 and abs(py - (room_y + room_h // 2)) <= 1:
                        continue
                    grid[py][px] = "#"

            if room_w >= 6 and room_h >= 6 and random.random() < 0.75:
                spacing_x = random.randint(2, 3)
                spacing_y = random.randint(2, 3)
                start_x = room_x + 1 + random.randint(0, 1)
                start_y = room_y + 1 + random.randint(0, 1)
                for py in range(start_y, room_y + room_h - 1, spacing_y):
                    for px in range(start_x, room_x + room_w - 1, spacing_x):
                        if random.random() < 0.55:
                            grid[py][px] = "#"

        return ["".join(row) for row in grid]

    def generate_new_level(self, initial=False):
        best_candidate = None
        candidate_sizes = [self.choose_map_size()]
        candidate_sizes.extend(entry for entry in MAP_SIZES if entry[0] != candidate_sizes[0][0])

        for size_name, width, height in candidate_sizes:
            for _ in range(8):
                candidate_map = self.generate_procedural_map(width, height)
                self.map_layout = candidate_map
                spawn_x, spawn_y = self.safe_player_spawn()
                floor_count = sum(row.count(".") for row in candidate_map)

                if best_candidate is None or floor_count > best_candidate["floor_count"]:
                    best_candidate = {
                        "map_layout": candidate_map,
                        "spawn": (spawn_x, spawn_y),
                        "size_name": size_name,
                        "floor_count": floor_count,
                    }

                if self.corner_coverage_ok(spawn_x, spawn_y):
                    self.map_size_name = size_name
                    self.player_x, self.player_y = spawn_x, spawn_y
                    break
            else:
                continue
            break
        else:
            if best_candidate is not None:
                self.map_layout = best_candidate["map_layout"]
                self.map_size_name = best_candidate["size_name"]
                self.player_x, self.player_y = best_candidate["spawn"]
            else:
                self.map_layout = list(MAP_LAYOUT)
                self.map_size_name = "small"
                self.player_x, self.player_y = self.safe_player_spawn()

        self.zombies = []
        self.loot_boxes = []
        self.collected_loot_ids = set()
        self.next_loot_id = 1
        self.spawn_index = 0
        self.spawn_timer = SPAWN_INTERVAL
        self.rebuild_spawn_points()
        self.player_angle = 0.0
        self.move_velocity_x = 0.0
        self.move_velocity_y = 0.0
        self.turn_velocity = 0.0
        self.selected_slot = None
        self.drag_item = None
        self.drag_origin = None
        self.spawn_zombie("walker")
        self.spawn_zombie("runner")
        self.spawn_zombie("brute")
        if not initial:
            self.level_index += 1
            self.set_message(f"Entered {self.map_size_name} level {self.level_index}", 2.0)

    def make_zombie(self, zombie_type_name, x, y):
        zombie_type = next(
            zombie_type for zombie_type in ZOMBIE_TYPES if zombie_type["name"] == zombie_type_name
        )
        return {
            "x": x,
            "y": y,
            "hp": zombie_type["hp"],
            "max_hp": zombie_type["hp"],
            "cooldown": 0.0,
            "alive": True,
            "type": zombie_type["name"],
            "speed": zombie_type["speed"],
            "damage": zombie_type["damage"],
            "color_bias": zombie_type["color_bias"],
        }

    def set_message(self, text, duration=1.8):
        self.message = text
        self.message_timer = duration

    def toggle_inventory(self, force=None):
        target_state = (not self.inventory_open) if force is None else force
        self.inventory_open = target_state
        self.selected_slot = None
        self.inventory_buttons = {}
        if not self.inventory_open and self.drag_item is not None and self.drag_origin is not None:
            self.inventory[self.drag_origin] = self.drag_item
            self.drag_item = None
            self.drag_origin = None

    def toggle_pause_menu(self, force=None):
        target_state = (not self.pause_menu_open) if force is None else force
        self.pause_menu_open = target_state
        self.pause_buttons = {}

    def toggle_map_view(self, force=None):
        target_state = (not self.map_view_open) if force is None else force
        self.map_view_open = target_state

    def current_gun(self):
        return GUNS[self.gun_index]

    def clamp_reserve_ammo(self):
        self.reserve_ammo = clamp(int(self.reserve_ammo), 0, MAX_RESERVE_AMMO)

    def add_reserve_ammo(self, amount):
        self.reserve_ammo = clamp(int(self.reserve_ammo + amount), 0, MAX_RESERVE_AMMO)

    def sync_gun_ammo_on_upgrade(self):
        gun = self.current_gun()
        if gun.get("melee"):
            self.mag_ammo = 1
            return
        self.mag_ammo = min(self.mag_ammo, gun["magazine"])
        self.clamp_reserve_ammo()
        if self.mag_ammo <= 0:
            self.mag_ammo = min(gun["magazine"], max(1, self.reserve_ammo))

    def make_item(self, item_type, count=1, gun_index=None):
        item = {"type": item_type, "count": count}
        if gun_index is not None:
            item["gun_index"] = gun_index
        if item_type == "food":
            item["heal"] = random.randint(18, 28)
        if item_type == "ammo":
            item["ammo_gain"] = random.randint(16, 24)
        return item

    def is_stackable(self, item):
        return item["type"] in {"food", "materials", "ammo"}

    def max_stack_size(self, item_type):
        if item_type in {"food", "materials", "ammo"}:
            return 5
        return 1

    def item_label(self, item):
        if item["type"] == "food":
            return "Food"
        if item["type"] == "materials":
            return "Build Mats"
        if item["type"] == "ammo":
            return "Ammo"
        if item["type"] == "gun":
            return GUNS[item["gun_index"]]["name"]
        return item["type"].title()

    def item_colors(self, item):
        if item["type"] == "food":
            return "#7ed957", "#d04d3f"
        if item["type"] == "materials":
            return "#cfb287", "#7c6249"
        if item["type"] == "ammo":
            return "#d7d7d7", "#a67740"
        if item["type"] == "gun":
            return "#ffd77d", "#6f5b32"
        return "#cccccc", "#666666"

    def add_item_to_inventory(self, item):
        if self.is_stackable(item):
            for slot in self.inventory:
                if slot and slot["type"] == item["type"] and slot["count"] < self.max_stack_size(item["type"]):
                    available = self.max_stack_size(item["type"]) - slot["count"]
                    moved = min(available, item["count"])
                    slot["count"] += moved
                    item["count"] -= moved
                    if item["count"] == 0:
                        return True

        for index, slot in enumerate(self.inventory):
            if slot is None:
                new_item = dict(item)
                if self.is_stackable(new_item):
                    new_item["count"] = min(new_item["count"], self.max_stack_size(new_item["type"]))
                    item["count"] -= new_item["count"]
                    self.inventory[index] = new_item
                    if item["count"] <= 0:
                        return True
                else:
                    self.inventory[index] = new_item
                    return True
        return False

    def normalize_inventory(self):
        rebuilt = [None for _ in range(INVENTORY_SLOTS)]
        old_inventory = self.inventory
        self.inventory = rebuilt
        seen_gun_indices = set()

        for item in old_inventory:
            if item is None:
                continue
            normalized_item = dict(item)
            if self.is_stackable(normalized_item):
                normalized_item["count"] = max(1, int(normalized_item.get("count", 1)))
                while normalized_item["count"] > 0:
                    chunk = min(normalized_item["count"], self.max_stack_size(normalized_item["type"]))
                    if not self.add_item_to_inventory(self.make_item(normalized_item["type"], chunk)):
                        break
                    normalized_item["count"] -= chunk
            else:
                if normalized_item["type"] == "gun":
                    gun_index = int(normalized_item.get("gun_index", 0))
                    if gun_index <= self.gun_index or gun_index in seen_gun_indices:
                        continue
                    normalized_item["gun_index"] = gun_index
                    seen_gun_indices.add(gun_index)
                self.add_item_to_inventory(normalized_item)

    def normalize_loot_boxes(self, loaded_loot_boxes):
        normalized = []
        next_id = 1
        seen_keys = set()
        for loot in loaded_loot_boxes:
            if not isinstance(loot, dict):
                continue
            if not {"x", "y", "type"}.issubset(loot.keys()):
                continue
            loot_type = loot["type"]
            dedupe_key = (round(float(loot["x"]), 2), round(float(loot["y"]), 2), loot_type)
            if dedupe_key in seen_keys:
                continue
            normalized_loot = {
                "id": int(loot.get("id", next_id)),
                "x": float(loot["x"]),
                "y": float(loot["y"]),
                "type": loot_type,
            }
            if normalized_loot["id"] in self.collected_loot_ids:
                continue
            normalized.append(normalized_loot)
            seen_keys.add(dedupe_key)
            next_id = max(next_id, normalized_loot["id"] + 1)
        self.loot_boxes = normalized
        self.next_loot_id = max(self.next_loot_id, next_id)

    def count_item_type(self, item_type):
        total = 0
        for slot in self.inventory:
            if slot and slot["type"] == item_type:
                total += slot["count"]
        return total

    def remove_item_type(self, item_type, count):
        remaining = count
        for index, slot in enumerate(self.inventory):
            if not slot or slot["type"] != item_type:
                continue
            taken = min(slot["count"], remaining)
            slot["count"] -= taken
            remaining -= taken
            if slot["count"] <= 0:
                self.inventory[index] = None
            if remaining == 0:
                return True
        return False

    def selected_item(self):
        if self.selected_slot is None:
            return None
        return self.inventory[self.selected_slot]

    def inventory_panel_rect(self):
        width = 760
        height = 390
        x0 = (SCREEN_WIDTH - width) / 2
        y0 = (SCREEN_HEIGHT - height) / 2
        return x0, y0, x0 + width, y0 + height

    def inventory_slot_rect(self, slot_index):
        panel_x0, panel_y0, _panel_x1, _panel_y1 = self.inventory_panel_rect()
        grid_x = slot_index % INVENTORY_COLS
        grid_y = slot_index // INVENTORY_COLS
        x0 = panel_x0 + 26 + grid_x * (SLOT_SIZE + SLOT_GAP)
        y0 = panel_y0 + 72 + grid_y * (SLOT_SIZE + SLOT_GAP)
        return x0, y0, x0 + SLOT_SIZE, y0 + SLOT_SIZE

    def inventory_slot_at(self, x, y):
        for index in range(INVENTORY_SLOTS):
            x0, y0, x1, y1 = self.inventory_slot_rect(index)
            if x0 <= x <= x1 and y0 <= y <= y1:
                return index
        return None

    def weighted_loot_type(self):
        roll = random.random() * 100
        if roll < 40:
            return "ammo"
        if roll < 70:
            return "food"
        if roll < 95:
            return "materials"
        return "gun"

    def next_loot_gun_index(self):
        return min(self.gun_index + 1, len(GUNS) - 1)

    def has_gun_item(self, gun_index):
        return any(slot and slot["type"] == "gun" and slot.get("gun_index") == gun_index for slot in self.inventory)

    def equipment_slot_rect(self):
        x0, y0, x1, _y1 = self.inventory_panel_rect()
        slot_x0 = x1 - 210
        slot_y0 = y0 + 84
        return slot_x0, slot_y0, slot_x0 + SLOT_SIZE, slot_y0 + SLOT_SIZE

    def equip_gun_to_slot(self, new_index, source_slot=None):
        previous_index = self.gun_index
        if new_index == previous_index:
            self.set_message(f"{self.current_gun()['name']} is already equipped", 1.0)
            return

        previous_item = self.make_item("gun", 1, previous_index) if previous_index != 0 else None
        target_slot_available = source_slot is not None and self.inventory[source_slot] is None
        if previous_item is not None and not target_slot_available and not any(slot is None for slot in self.inventory):
            self.set_message("Need space to swap equipped gun", 1.2)
            return

        self.gun_index = new_index
        self.sync_gun_ammo_on_upgrade()
        if not self.current_gun().get("melee"):
            self.add_reserve_ammo(self.current_gun()["ammo_drop"])

        if source_slot is not None:
            self.inventory[source_slot] = None

        if previous_item is not None:
            if source_slot is not None and self.inventory[source_slot] is None:
                self.inventory[source_slot] = previous_item
            else:
                self.add_item_to_inventory(previous_item)

        self.set_message(f"Equipped {self.current_gun()['name']}")

    def maybe_drop_loot(self, x, y):
        if random.random() > LOOT_DROP_CHANCE:
            return

        loot_type = self.weighted_loot_type()
        loot = {"id": self.next_loot_id, "x": x, "y": y, "type": loot_type}
        if loot_type == "materials":
            loot["count"] = random.randint(1, 4)
        self.loot_boxes.append(loot)
        self.next_loot_id += 1

    def start_reload(self):
        gun = self.current_gun()
        if self.game_over or self.inventory_open or self.reload_timer > 0.0:
            return
        if gun.get("melee"):
            self.set_message("Knife does not reload", 1.0)
            return
        if self.mag_ammo >= gun["magazine"]:
            self.set_message("Magazine already full", 1.0)
            return
        if self.reserve_ammo <= 0:
            self.set_message("No reserve ammo", 1.0)
            return
        self.reload_timer = gun["reload_time"]
        self.set_message(f"Reloading {gun['name']}...", gun["reload_time"])

    def finish_reload(self):
        gun = self.current_gun()
        needed = gun["magazine"] - self.mag_ammo
        loaded = min(needed, self.reserve_ammo)
        self.mag_ammo += loaded
        self.reserve_ammo -= loaded
        self.clamp_reserve_ammo()
        self.set_message(f"Reloaded {gun['name']}", 1.0)

    def handle_inventory_action(self, action):
        item = self.selected_item()
        if item is None:
            return

        if action == "use_food" and item["type"] == "food":
            if self.player_hp >= PLAYER_MAX_HP:
                self.set_message("HP already full", 1.0)
                return
            heal_amount = int(item.get("heal", FOOD_HEAL))
            self.player_hp = min(PLAYER_MAX_HP, self.player_hp + heal_amount)
            item["count"] -= 1
            if item["count"] <= 0:
                self.inventory[self.selected_slot] = None
            self.set_message(f"Ate food and recovered {heal_amount} HP")
        elif action == "equip_gun" and item["type"] == "gun":
            self.equip_gun_to_slot(item["gun_index"], self.selected_slot)
        elif action == "use_ammo" and item["type"] == "ammo":
            ammo_gain = int(item.get("ammo_gain", 20))
            item["count"] -= 1
            if item["count"] <= 0:
                self.inventory[self.selected_slot] = None
            self.add_reserve_ammo(ammo_gain)
            self.set_message(f"Stored {ammo_gain} ammo from 1 item")
        elif action == "craft_ammo" and item["type"] == "materials":
            if item["count"] < 1:
                self.set_message("Need 1 material", 1.0)
                return
            item["count"] -= 1
            if item["count"] <= 0:
                self.inventory[self.selected_slot] = None
            if self.add_item_to_inventory(self.make_item("ammo", 1)):
                self.set_message("Crafted 1 ammo item from 1 material")
            else:
                self.add_item_to_inventory(self.make_item("materials", 1))
                self.set_message("Need space to craft ammo", 1.0)
        elif action.startswith("craft_gun_") and item["type"] == "materials":
            gun_index = int(action.split("_")[-1])
            gun = GUNS[gun_index]
            if self.gun_index >= gun_index or self.has_gun_item(gun_index):
                self.set_message(f"{gun['name']} already unlocked", 1.2)
                return
            if self.count_item_type("materials") < gun["craft_cost"]:
                self.set_message(f"Need {gun['craft_cost']} materials", 1.2)
                return
            if not any(slot is None for slot in self.inventory):
                self.set_message("Need an empty inventory slot", 1.2)
                return
            self.remove_item_type("materials", gun["craft_cost"])
            self.add_item_to_inventory(self.make_item("gun", 1, gun_index))
            self.set_message(f"Crafted {gun['name']}")

    def handle_pause_action(self, action):
        if action == "save_game":
            self.save_game()
            return
        if action == "load_game":
            self.load_game()
            return
        if action == "resume_game":
            self.toggle_pause_menu(False)
            return
        if action == "quit_game":
            self.root.destroy()

    def reset_run(self):
        self.player_hp = PLAYER_MAX_HP
        self.gun_index = 0
        self.reserve_ammo = GUNS[1]["magazine"] * 6
        self.mag_ammo = 1
        self.inventory = [None for _ in range(INVENTORY_SLOTS)]
        self.zombies = []
        self.loot_boxes = []
        self.collected_loot_ids = set()
        self.next_loot_id = 1
        self.spawn_index = 0
        self.spawn_timer = SPAWN_INTERVAL
        self.level_index = 1
        self.kill_count = 0
        self.move_velocity_x = 0.0
        self.move_velocity_y = 0.0
        self.turn_velocity = 0.0
        self.reload_timer = 0.0
        self.inventory_open = False
        self.pause_menu_open = False
        self.map_view_open = False
        self.selected_slot = None
        self.drag_item = None
        self.drag_origin = None
        self.game_over = False
        self.generate_new_level(initial=True)
        self.set_message("Started a new run", 1.4)

    def handle_death_action(self, action):
        if action == "retry_run":
            self.reset_run()
            return
        if action == "load_save":
            self.game_over = False
            self.load_game()

    def save_game(self):
        active_loot_boxes = [
            loot for loot in self.loot_boxes
            if loot.get("id") not in self.collected_loot_ids
        ]
        save_data = {
            "player": {
                "x": self.player_x,
                "y": self.player_y,
                "angle": self.player_angle,
                "hp": self.player_hp,
                "move_velocity_x": self.move_velocity_x,
                "move_velocity_y": self.move_velocity_y,
                "turn_velocity": self.turn_velocity,
            },
            "weapon": {
                "gun_index": self.gun_index,
                "reserve_ammo": self.reserve_ammo,
                "mag_ammo": self.mag_ammo,
                "reload_timer": self.reload_timer,
            },
            "world": {
                "map_layout": self.map_layout,
                "map_size_name": self.map_size_name,
                "level_index": self.level_index,
                "kill_count": self.kill_count,
                "spawn_index": self.spawn_index,
                "spawn_timer": self.spawn_timer,
                "loot_boxes": active_loot_boxes,
                "collected_loot_ids": sorted(self.collected_loot_ids),
                "next_loot_id": self.next_loot_id,
                "zombies": self.zombies,
            },
            "inventory": self.inventory,
            "meta": {
                "format": "dpy",
                "version": 1,
                "saved_at": time.time(),
            },
        }
        with open(SAVE_FILE, "w", encoding="utf-8") as save_file:
            json.dump(save_data, save_file, indent=2)
        self.set_message(f"Saved to {SAVE_FILE}", 1.4)

    def load_game(self):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as save_file:
                save_data = json.load(save_file)
        except FileNotFoundError:
            self.set_message(f"No {SAVE_FILE} found", 1.4)
            return
        except json.JSONDecodeError:
            self.set_message(f"{SAVE_FILE} is corrupted", 1.4)
            return

        player = save_data.get("player", {})
        weapon = save_data.get("weapon", {})
        world = save_data.get("world", {})

        self.player_x = player.get("x", self.player_x)
        self.player_y = player.get("y", self.player_y)
        self.player_angle = player.get("angle", self.player_angle)
        self.move_velocity_x = float(player.get("move_velocity_x", 0.0))
        self.move_velocity_y = float(player.get("move_velocity_y", 0.0))
        self.turn_velocity = float(player.get("turn_velocity", 0.0))
        self.player_hp = clamp(player.get("hp", self.player_hp), 0, PLAYER_MAX_HP)

        self.gun_index = clamp(weapon.get("gun_index", self.gun_index), 0, len(GUNS) - 1)
        self.reserve_ammo = max(0, int(weapon.get("reserve_ammo", self.reserve_ammo)))
        self.mag_ammo = max(0, int(weapon.get("mag_ammo", self.mag_ammo)))
        self.reload_timer = max(0.0, float(weapon.get("reload_timer", 0.0)))

        inventory = save_data.get("inventory", self.inventory)
        if isinstance(inventory, list):
            normalized = inventory[:INVENTORY_SLOTS]
            while len(normalized) < INVENTORY_SLOTS:
                normalized.append(None)
            self.inventory = normalized
            self.normalize_inventory()

        loaded_map = world.get("map_layout")
        if isinstance(loaded_map, list) and loaded_map:
            self.map_layout = [str(row) for row in loaded_map]
        else:
            self.map_layout = list(MAP_LAYOUT)
        self.map_size_name = str(world.get("map_size_name", self.map_size_name))
        self.rebuild_spawn_points()
        if self.is_position_blocked(self.player_x, self.player_y, PLAYER_RADIUS):
            self.player_x, self.player_y = self.safe_player_spawn()

        self.level_index = int(world.get("level_index", self.level_index))
        self.kill_count = int(world.get("kill_count", self.kill_count))
        self.collected_loot_ids = {int(value) for value in world.get("collected_loot_ids", [])}
        self.next_loot_id = int(world.get("next_loot_id", self.next_loot_id))
        self.normalize_loot_boxes(world.get("loot_boxes", []))
        self.zombies = world.get("zombies", [])
        self.spawn_index = int(world.get("spawn_index", self.spawn_index))
        self.spawn_timer = float(world.get("spawn_timer", self.spawn_timer))

        self.game_over = self.player_hp <= 0
        self.selected_slot = None
        self.drag_item = None
        self.drag_origin = None
        self.sync_gun_ammo_on_upgrade()
        self.set_message(f"Loaded {SAVE_FILE}", 1.4)

    def spawn_zombie(self, zombie_type_name=None, x=None, y=None):
        living_zombies = sum(1 for zombie in self.zombies if zombie["alive"])
        if living_zombies >= MAX_LIVING_ZOMBIES:
            return

        zombie_type_name = zombie_type_name or ZOMBIE_TYPES[self.spawn_index % len(ZOMBIE_TYPES)]["name"]
        if x is None or y is None:
            start_index = self.spawn_index % len(self.spawn_points)
            for offset in range(len(self.spawn_points)):
                spawn_x, spawn_y = self.spawn_points[(start_index + offset) % len(self.spawn_points)]
                if not self.can_spawn_at(spawn_x, spawn_y, ZOMBIE_RADIUS):
                    continue
                x, y = spawn_x, spawn_y
                break
            else:
                return
        elif not self.can_spawn_at(x, y, ZOMBIE_RADIUS):
            return

        self.zombies.append(self.make_zombie(zombie_type_name, x, y))
        self.spawn_index += 1

    def update_player(self, dt):
        if self.game_over:
            return

        forward = 0
        strafe = 0
        turn = 0

        if "w" in self.keys or "up" in self.keys:
            forward += 1
        if "s" in self.keys or "down" in self.keys:
            forward -= 1
        if "a" in self.keys:
            strafe -= 1
        if "d" in self.keys:
            strafe += 1
        if "left" in self.keys:
            turn -= 1
        if "right" in self.keys:
            turn += 1

        target_turn_velocity = turn * TURN_SPEED
        turn_change = TURN_ACCEL * dt if turn != 0 else TURN_DECEL * dt
        if self.turn_velocity < target_turn_velocity:
            self.turn_velocity = min(self.turn_velocity + turn_change, target_turn_velocity)
        elif self.turn_velocity > target_turn_velocity:
            self.turn_velocity = max(self.turn_velocity - turn_change, target_turn_velocity)
        self.turn_velocity = clamp(self.turn_velocity, -TURN_SPEED, TURN_SPEED)
        self.player_angle += self.turn_velocity * dt

        sin_a = math.sin(self.player_angle)
        cos_a = math.cos(self.player_angle)
        target_vx = (cos_a * forward - sin_a * strafe) * MOVE_SPEED
        target_vy = (sin_a * forward + cos_a * strafe) * MOVE_SPEED

        accel = MOVE_ACCEL * dt
        decel = MOVE_DECEL * dt
        change_x = accel if abs(target_vx) > 0.001 else decel
        change_y = accel if abs(target_vy) > 0.001 else decel

        if self.move_velocity_x < target_vx:
            self.move_velocity_x = min(self.move_velocity_x + change_x, target_vx)
        elif self.move_velocity_x > target_vx:
            self.move_velocity_x = max(self.move_velocity_x - change_x, target_vx)

        if self.move_velocity_y < target_vy:
            self.move_velocity_y = min(self.move_velocity_y + change_y, target_vy)
        elif self.move_velocity_y > target_vy:
            self.move_velocity_y = max(self.move_velocity_y - change_y, target_vy)

        planar_speed = math.hypot(self.move_velocity_x, self.move_velocity_y)
        if planar_speed > MOVE_SPEED:
            scale = MOVE_SPEED / planar_speed
            self.move_velocity_x *= scale
            self.move_velocity_y *= scale

        self.try_move(self.player_x + self.move_velocity_x * dt, self.player_y + self.move_velocity_y * dt)

    def update_zombies(self, dt):
        if self.game_over:
            return

        for zombie in self.zombies:
            if not zombie["alive"]:
                continue

            zombie["cooldown"] = max(0.0, zombie["cooldown"] - dt)
            dx = self.player_x - zombie["x"]
            dy = self.player_y - zombie["y"]
            distance = math.hypot(dx, dy)

            if distance <= ZOMBIE_ATTACK_RANGE:
                if zombie["cooldown"] <= 0.0:
                    self.player_hp = max(0, self.player_hp - zombie["damage"])
                    zombie["cooldown"] = ZOMBIE_ATTACK_COOLDOWN
                    if self.player_hp <= 0:
                        self.game_over = True
                continue

            if distance <= 0.0001:
                continue

            step = zombie["speed"] * dt
            move_x = zombie["x"] + (dx / distance) * step
            move_y = zombie["y"] + (dy / distance) * step

            if not self.is_position_blocked(move_x, zombie["y"], ZOMBIE_RADIUS):
                zombie["x"] = move_x
            if not self.is_position_blocked(zombie["x"], move_y, ZOMBIE_RADIUS):
                zombie["y"] = move_y

        self.spawn_timer -= dt
        if self.spawn_timer <= 0.0:
            self.spawn_timer = SPAWN_INTERVAL
            self.spawn_zombie()

    def collect_loot(self):
        if self.game_over or self.inventory_open:
            return

        remaining_loot = []
        for loot in self.loot_boxes:
            loot_id = loot.get("id")
            if loot_id in self.collected_loot_ids:
                continue
            distance = math.hypot(self.player_x - loot["x"], self.player_y - loot["y"])
            if distance > LOOT_PICKUP_RANGE:
                remaining_loot.append(loot)
                continue

            if loot["type"] == "food":
                added = self.add_item_to_inventory(self.make_item("food", 1))
                message = "Picked up food"
            elif loot["type"] == "ammo":
                added = self.add_item_to_inventory(self.make_item("ammo", 1))
                message = "Picked up ammo"
            elif loot["type"] == "materials":
                material_count = int(loot.get("count", 1))
                added = self.add_item_to_inventory(self.make_item("materials", material_count))
                message = f"Picked up {material_count} building material{'s' if material_count != 1 else ''}"
            else:
                added = self.add_item_to_inventory(self.make_item("materials", 2))
                message = "Recovered legacy gun drop as materials"

            if added:
                if loot_id is not None:
                    self.collected_loot_ids.add(loot_id)
                loot["collected"] = True
                self.set_message(message)
            else:
                remaining_loot.append(loot)
                self.set_message("Inventory full", 1.0)

        self.loot_boxes = [loot for loot in remaining_loot if not loot.get("collected")]

    def fire_weapon(self):
        if self.game_over or self.inventory_open:
            return

        now = time.perf_counter()
        gun = self.current_gun()
        is_melee = gun.get("melee", False)
        if self.reload_timer > 0.0:
            return
        if now - self.last_shot_time < gun["cooldown"]:
            return
        if not is_melee and self.mag_ammo <= 0:
            self.set_message("Out of ammo - press R", 1.0)
            return

        self.last_shot_time = now
        self.muzzle_flash = 0.08
        if not is_melee:
            self.mag_ammo -= 1

        best_target = None
        best_distance = MAX_DEPTH
        aim_threshold = math.radians(20 if is_melee else 7.5)
        max_range = gun.get("range", MAX_DEPTH if is_melee else MAX_DEPTH)

        for zombie in self.zombies:
            if not zombie["alive"]:
                continue

            dx = zombie["x"] - self.player_x
            dy = zombie["y"] - self.player_y
            distance = math.hypot(dx, dy)
            if distance > max_range:
                continue

            angle_to_zombie = math.atan2(dy, dx)
            angle_diff = (angle_to_zombie - self.player_angle + math.pi) % (2 * math.pi) - math.pi
            if abs(angle_diff) > aim_threshold:
                continue

            if not is_melee:
                wall_distance, _hit_vertical, _texture_u = self.cast_ray(angle_to_zombie)
                if wall_distance + 0.05 < distance:
                    continue
            elif distance > gun.get("range", 1.25):
                continue

            if distance < best_distance:
                best_target = zombie
                best_distance = distance

        if best_target is not None:
            best_target["hp"] -= gun["damage"]
            if best_target["hp"] <= 0:
                best_target["alive"] = False
                self.kill_count += 1
                self.maybe_drop_loot(best_target["x"], best_target["y"])
                if self.kill_count % LEVEL_KILL_TARGET == 0:
                    self.generate_new_level()

    def cast_ray(self, angle):
        step = 0.02
        depth = 0.0
        x = self.player_x
        y = self.player_y

        while depth < MAX_DEPTH:
            x += math.cos(angle) * step
            y += math.sin(angle) * step
            depth += step
            if self.is_wall(x, y):
                hit_vertical = abs(x - round(x)) < abs(y - round(y))
                texture_u = y % 1.0 if hit_vertical else x % 1.0
                return depth, hit_vertical, texture_u

        return MAX_DEPTH, False, 0.0

    def draw_background(self):
        for y in range(0, HALF_HEIGHT, 4):
            blend = y / HALF_HEIGHT
            sky = rgb(64 + 60 * blend, 116 + 70 * blend, 155 + 55 * blend)
            self.canvas.create_rectangle(0, y, SCREEN_WIDTH, y + 4, fill=sky, outline="")

        self.canvas.create_oval(60, 50, 190, 180, fill="#ffd779", outline="")
        self.canvas.create_oval(78, 66, 208, 196, fill="#ffe8a8", outline="")

        for cloud_x, cloud_y, scale in [(620, 88, 1.0), (760, 122, 0.85), (360, 92, 0.72)]:
            self.canvas.create_oval(
                cloud_x,
                cloud_y,
                cloud_x + 70 * scale,
                cloud_y + 34 * scale,
                fill="#f4f8ff",
                outline="",
            )
            self.canvas.create_oval(
                cloud_x + 20 * scale,
                cloud_y - 10 * scale,
                cloud_x + 92 * scale,
                cloud_y + 30 * scale,
                fill="#f4f8ff",
                outline="",
            )
            self.canvas.create_oval(
                cloud_x + 44 * scale,
                cloud_y,
                cloud_x + 116 * scale,
                cloud_y + 34 * scale,
                fill="#f4f8ff",
                outline="",
            )

        self.canvas.create_rectangle(0, HALF_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT, fill="#3f2f22", outline="")

        for y in range(HALF_HEIGHT, SCREEN_HEIGHT, 4):
            distance_ratio = (y - HALF_HEIGHT) / HALF_HEIGHT
            base = 76 - distance_ratio * 42
            stripe = 10 if (y // 20) % 2 == 0 else -4
            floor = rgb(base + stripe, base * 0.72 + stripe, base * 0.42 + stripe * 0.4)
            self.canvas.create_rectangle(0, y, SCREEN_WIDTH, y + 4, fill=floor, outline="")

    def build_wall_renderables(self):
        projection = (SCREEN_WIDTH / 2) / math.tan(FOV / 2)
        column_width = SCREEN_WIDTH / NUM_RAYS
        start_angle = self.player_angle - FOV / 2
        self.wall_depths = [MAX_DEPTH] * NUM_RAYS
        renderables = []

        for ray in range(NUM_RAYS):
            ray_angle = start_angle + (ray / NUM_RAYS) * FOV
            raw_depth, hit_vertical, texture_u = self.cast_ray(ray_angle)
            corrected_depth = raw_depth * math.cos(ray_angle - self.player_angle)
            corrected_depth = max(corrected_depth, 0.0001)
            self.wall_depths[ray] = corrected_depth
            wall_height = min(int((TILE_SIZE / corrected_depth) * projection), SCREEN_HEIGHT)

            brightness = max(36, min(255, int(215 / (1 + corrected_depth * 0.22))))
            if hit_vertical:
                brightness = int(brightness * 0.84)

            x0 = ray * column_width
            y0 = HALF_HEIGHT - wall_height / 2
            y1 = HALF_HEIGHT + wall_height / 2

            mortar = 0.06 if (texture_u % 0.25) < 0.035 else 0.0
            brick_band = int((wall_height / 24) + (ray % 2))
            brick_variation = -18 if brick_band % 2 == 0 else 10
            crack = -26 if abs(texture_u - 0.5) < 0.025 else 0
            r = brightness + brick_variation + crack - mortar * 110
            g = brightness * 0.60 + brick_variation * 0.45 + crack * 0.2 - mortar * 90
            b = brightness * 0.42 + brick_variation * 0.2 - mortar * 70
            renderables.append(
                {
                    "kind": "wall",
                    "distance": corrected_depth,
                    "x0": x0,
                    "y0": y0,
                    "x1": x0 + column_width + 1,
                    "y1": y1,
                    "base_color": rgb(r, g, b),
                    "highlight_color": rgb(r + 18, g + 14, b + 10),
                    "mortar": mortar,
                    "ray": ray,
                    "wall_height": wall_height,
                }
            )

        return renderables

    def build_zombie_renderables(self):
        projection = (SCREEN_WIDTH / 2) / math.tan(FOV / 2)
        renderables = []

        for zombie in self.zombies:
            if not zombie["alive"]:
                continue

            dx = zombie["x"] - self.player_x
            dy = zombie["y"] - self.player_y
            distance = math.hypot(dx, dy)
            if distance <= 0.05:
                continue

            angle = math.atan2(dy, dx) - self.player_angle
            angle = (angle + math.pi) % (2 * math.pi) - math.pi
            if abs(angle) > FOV / 2 + 0.35:
                continue

            screen_x = SCREEN_WIDTH / 2 + math.tan(angle) * projection
            perceived_distance = max(distance * 1.35, 0.05)
            size = max(12, int((0.72 / perceived_distance) * projection))
            x0 = int(screen_x - size / 2)
            x1 = int(screen_x + size / 2)
            if x1 < 0 or x0 >= SCREEN_WIDTH:
                continue

            ray_index = max(0, min(NUM_RAYS - 1, int((screen_x / SCREEN_WIDTH) * NUM_RAYS)))
            if distance >= self.wall_depths[ray_index]:
                continue

            body_top = HALF_HEIGHT - size * 0.18
            body_bottom = HALF_HEIGHT + size * 0.62
            head_size = size * 0.36
            brightness = max(70, min(220, int(210 / (1 + distance * 0.18))))
            bias_r, bias_g, bias_b = zombie["color_bias"]
            coat = rgb(brightness * 0.18 + bias_r, brightness * 0.42 + bias_g, brightness * 0.20 + bias_b)
            coat_shadow = rgb(
                brightness * 0.10 + bias_r * 0.5,
                brightness * 0.24 + bias_g * 0.5,
                brightness * 0.12 + bias_b * 0.5,
            )
            skin = rgb(brightness * 0.78, brightness * 0.88, brightness * 0.62)
            eye = "#ff4d4d"
            blood = "#792222"

            leg_w = size * 0.22
            arm_w = size * 0.16

            self.canvas.create_rectangle(
                screen_x - size * 0.36,
                body_top,
                screen_x + size * 0.36,
                body_bottom,
                fill=coat,
                outline="#111111",
            )
            self.canvas.create_rectangle(
                screen_x - size * 0.08,
                body_top,
                screen_x + size * 0.08,
                body_bottom,
                fill=coat_shadow,
                outline="",
            )
            self.canvas.create_oval(
                screen_x - head_size / 2,
                body_top - head_size * 0.8,
                screen_x + head_size / 2,
                body_top + head_size * 0.2,
                fill=skin,
                outline="#111111",
            )
            self.canvas.create_rectangle(
                screen_x - size * 0.46,
                body_top + size * 0.08,
                screen_x - size * 0.30,
                body_top + size * 0.52,
                fill=coat,
                outline="#111111",
            )
            self.canvas.create_rectangle(
                screen_x + size * 0.30,
                body_top + size * 0.08,
                screen_x + size * 0.46,
                body_top + size * 0.52,
                fill=coat,
                outline="#111111",
            )
            self.canvas.create_rectangle(
                screen_x - leg_w - 3,
                body_bottom,
                screen_x - 3,
                body_bottom + size * 0.30,
                fill="#3d2b2b",
                outline="#111111",
            )
            self.canvas.create_rectangle(
                screen_x + 3,
                body_bottom,
                screen_x + leg_w + 3,
                body_bottom + size * 0.30,
                fill="#3d2b2b",
                outline="#111111",
            )
            self.canvas.create_rectangle(
                screen_x - arm_w - size * 0.30,
                body_top + size * 0.28,
                screen_x - size * 0.30,
                body_top + size * 0.45,
                fill=skin,
                outline="",
            )
            self.canvas.create_rectangle(
                screen_x + size * 0.30,
                body_top + size * 0.28,
                screen_x + size * 0.30 + arm_w,
                body_top + size * 0.45,
                fill=skin,
                outline="",
            )
            self.canvas.create_oval(
                screen_x - head_size * 0.18,
                body_top - head_size * 0.43,
                screen_x - head_size * 0.05,
                body_top - head_size * 0.30,
                fill=eye,
                outline="",
            )
            self.canvas.create_oval(
                screen_x + head_size * 0.05,
                body_top - head_size * 0.43,
                screen_x + head_size * 0.18,
                body_top - head_size * 0.30,
                fill=eye,
                outline="",
            )
            self.canvas.create_line(
                screen_x - head_size * 0.12,
                body_top - head_size * 0.10,
                screen_x + head_size * 0.14,
                body_top - head_size * 0.02,
                fill=blood,
                width=max(1, int(size * 0.03)),
            )

            if zombie["hp"] < zombie["max_hp"]:
                bar_width = size * 0.8
                hp_ratio = max(0.0, zombie["hp"] / zombie["max_hp"])
                self.canvas.create_rectangle(
                    screen_x - bar_width / 2,
                    body_top - head_size * 1.05,
                    screen_x + bar_width / 2,
                    body_top - head_size * 0.92,
                    fill="#1a1a1a",
                    outline="#e6e6e6",
                )
                self.canvas.create_rectangle(
                    screen_x - bar_width / 2 + 1,
                    body_top - head_size * 1.05 + 1,
                    screen_x - bar_width / 2 + 1 + (bar_width - 2) * hp_ratio,
                    body_top - head_size * 0.92 - 1,
                    fill="#7dff6d",
                    outline="",
                )
            renderables.append(
                {
                    "kind": "zombie",
                    "distance": distance,
                    "screen_x": screen_x,
                    "size": size,
                    "body_top": body_top,
                    "body_bottom": body_bottom,
                    "head_size": head_size,
                    "coat": coat,
                    "coat_shadow": coat_shadow,
                    "skin": skin,
                    "eye": eye,
                    "blood": blood,
                    "leg_w": leg_w,
                    "arm_w": arm_w,
                    "hp": zombie["hp"],
                    "max_hp": zombie["max_hp"],
                }
            )

        return renderables

    def build_loot_renderables(self):
        projection = (SCREEN_WIDTH / 2) / math.tan(FOV / 2)
        renderables = []

        for loot in self.loot_boxes:
            if loot.get("id") in self.collected_loot_ids:
                continue
            dx = loot["x"] - self.player_x
            dy = loot["y"] - self.player_y
            distance = math.hypot(dx, dy)
            if distance <= 0.05:
                continue

            angle = math.atan2(dy, dx) - self.player_angle
            angle = (angle + math.pi) % (2 * math.pi) - math.pi
            if abs(angle) > FOV / 2 + 0.25:
                continue

            screen_x = SCREEN_WIDTH / 2 + math.tan(angle) * projection
            size = max(14, int((0.55 / distance) * projection))
            ray_index = max(0, min(NUM_RAYS - 1, int((screen_x / SCREEN_WIDTH) * NUM_RAYS)))
            if distance >= self.wall_depths[ray_index]:
                continue

            colors = {
                "food": ("#7ed957", "#d04d3f"),
                "materials": ("#cfb287", "#7c6249"),
                "ammo": ("#d7d7d7", "#a67740"),
                "gun": ("#7fd6ff", "#3f5363"),
            }
            main_color, accent = colors[loot["type"]]
            top = HALF_HEIGHT + size * 0.20
            bottom = top + size * 0.8
            left = screen_x - size / 2
            right = screen_x + size / 2
            renderables.append(
                {
                    "kind": "loot",
                    "distance": distance,
                    "screen_x": screen_x,
                    "size": size,
                    "top": top,
                    "bottom": bottom,
                    "left": left,
                    "right": right,
                    "main_color": main_color,
                    "accent": accent,
                    "loot_type": loot["type"],
                }
            )

        return renderables

    def draw_renderables(self):
        renderables = []
        renderables.extend(self.build_wall_renderables())
        renderables.extend(self.build_loot_renderables())
        renderables.extend(self.build_zombie_renderables())
        renderables.sort(key=lambda item: item["distance"], reverse=True)

        for item in renderables:
            if item["kind"] == "wall":
                self.canvas.create_rectangle(
                    item["x0"],
                    item["y0"],
                    item["x1"],
                    item["y1"],
                    fill=item["base_color"],
                    outline="",
                )
                if (item["ray"] % 8) < 4:
                    self.canvas.create_line(item["x0"], item["y0"], item["x0"], item["y1"], fill=item["highlight_color"])
                if item["mortar"] > 0:
                    self.canvas.create_line(item["x0"], item["y0"], item["x0"], item["y1"], fill="#7c6a57")
                if item["wall_height"] > 70:
                    mid_y = item["y0"] + (item["y1"] - item["y0"]) * 0.5
                    self.canvas.create_line(item["x0"], mid_y, item["x1"], mid_y, fill="#7b6552")
            elif item["kind"] == "loot":
                self.canvas.create_rectangle(item["left"], item["top"], item["right"], item["bottom"], fill=item["main_color"], outline="#111111", width=2)
                self.canvas.create_rectangle(
                    item["left"] + item["size"] * 0.14,
                    item["top"] + item["size"] * 0.18,
                    item["right"] - item["size"] * 0.14,
                    item["bottom"] - item["size"] * 0.18,
                    fill=item["accent"],
                    outline="",
                )
                if item["loot_type"] == "food":
                    self.canvas.create_oval(item["screen_x"] - item["size"] * 0.18, item["top"] + item["size"] * 0.20, item["screen_x"] + item["size"] * 0.18, item["top"] + item["size"] * 0.56, fill="#ffcf5a", outline="")
                elif item["loot_type"] == "ammo":
                    self.canvas.create_rectangle(item["screen_x"] - item["size"] * 0.08, item["top"] + item["size"] * 0.18, item["screen_x"] + item["size"] * 0.08, item["bottom"] - item["size"] * 0.12, fill="#f3c57a", outline="")
                    self.canvas.create_oval(item["screen_x"] - item["size"] * 0.08, item["top"] + item["size"] * 0.08, item["screen_x"] + item["size"] * 0.08, item["top"] + item["size"] * 0.24, fill="#c58b3a", outline="")
                elif item["loot_type"] == "materials":
                    self.canvas.create_line(item["left"] + item["size"] * 0.18, item["top"] + item["size"] * 0.24, item["right"] - item["size"] * 0.18, item["bottom"] - item["size"] * 0.20, fill="#f0e1c2", width=2)
                    self.canvas.create_line(item["left"] + item["size"] * 0.18, item["bottom"] - item["size"] * 0.20, item["right"] - item["size"] * 0.18, item["top"] + item["size"] * 0.24, fill="#f0e1c2", width=2)
                else:
                    self.canvas.create_rectangle(item["screen_x"] - item["size"] * 0.18, item["top"] + item["size"] * 0.20, item["screen_x"] + item["size"] * 0.18, item["bottom"] - item["size"] * 0.16, fill="#dfe9ef", outline="")
            elif item["kind"] == "zombie":
                screen_x = item["screen_x"]
                size = item["size"]
                body_top = item["body_top"]
                body_bottom = item["body_bottom"]
                head_size = item["head_size"]
                self.canvas.create_rectangle(
                    screen_x - size * 0.36,
                    body_top,
                    screen_x + size * 0.36,
                    body_bottom,
                    fill=item["coat"],
                    outline="#111111",
                )
                self.canvas.create_rectangle(
                    screen_x - size * 0.08,
                    body_top,
                    screen_x + size * 0.08,
                    body_bottom,
                    fill=item["coat_shadow"],
                    outline="",
                )
                self.canvas.create_oval(
                    screen_x - head_size / 2,
                    body_top - head_size * 0.8,
                    screen_x + head_size / 2,
                    body_top + head_size * 0.2,
                    fill=item["skin"],
                    outline="#111111",
                )
                self.canvas.create_rectangle(
                    screen_x - size * 0.46,
                    body_top + size * 0.08,
                    screen_x - size * 0.30,
                    body_top + size * 0.52,
                    fill=item["coat"],
                    outline="#111111",
                )
                self.canvas.create_rectangle(
                    screen_x + size * 0.30,
                    body_top + size * 0.08,
                    screen_x + size * 0.46,
                    body_top + size * 0.52,
                    fill=item["coat"],
                    outline="#111111",
                )
                self.canvas.create_rectangle(
                    screen_x - item["leg_w"] - 3,
                    body_bottom,
                    screen_x - 3,
                    body_bottom + size * 0.30,
                    fill="#3d2b2b",
                    outline="#111111",
                )
                self.canvas.create_rectangle(
                    screen_x + 3,
                    body_bottom,
                    screen_x + item["leg_w"] + 3,
                    body_bottom + size * 0.30,
                    fill="#3d2b2b",
                    outline="#111111",
                )
                self.canvas.create_rectangle(
                    screen_x - item["arm_w"] - size * 0.30,
                    body_top + size * 0.28,
                    screen_x - size * 0.30,
                    body_top + size * 0.45,
                    fill=item["skin"],
                    outline="",
                )
                self.canvas.create_rectangle(
                    screen_x + size * 0.30,
                    body_top + size * 0.28,
                    screen_x + size * 0.30 + item["arm_w"],
                    body_top + size * 0.45,
                    fill=item["skin"],
                    outline="",
                )
                self.canvas.create_oval(
                    screen_x - head_size * 0.18,
                    body_top - head_size * 0.43,
                    screen_x - head_size * 0.05,
                    body_top - head_size * 0.30,
                    fill=item["eye"],
                    outline="",
                )
                self.canvas.create_oval(
                    screen_x + head_size * 0.05,
                    body_top - head_size * 0.43,
                    screen_x + head_size * 0.18,
                    body_top - head_size * 0.30,
                    fill=item["eye"],
                    outline="",
                )
                self.canvas.create_line(
                    screen_x - head_size * 0.12,
                    body_top - head_size * 0.10,
                    screen_x + head_size * 0.14,
                    body_top - head_size * 0.02,
                    fill=item["blood"],
                    width=max(1, int(size * 0.03)),
                )
                if item["hp"] < item["max_hp"]:
                    bar_width = size * 0.8
                    hp_ratio = max(0.0, item["hp"] / item["max_hp"])
                    self.canvas.create_rectangle(
                        screen_x - bar_width / 2,
                        body_top - head_size * 1.05,
                        screen_x + bar_width / 2,
                        body_top - head_size * 0.92,
                        fill="#1a1a1a",
                        outline="#e6e6e6",
                    )
                    self.canvas.create_rectangle(
                        screen_x - bar_width / 2 + 1,
                        body_top - head_size * 1.05 + 1,
                        screen_x - bar_width / 2 + 1 + (bar_width - 2) * hp_ratio,
                        body_top - head_size * 0.92 - 1,
                        fill="#7dff6d",
                        outline="",
                    )

    def draw_minimap(self):
        offset_x = 12
        offset_y = 12
        view_diameter = MINIMAP_RADIUS_TILES * 2 + 1
        minimap_px = view_diameter * MINIMAP_SCALE
        world_origin_x = self.player_x - MINIMAP_RADIUS_TILES - 0.5
        world_origin_y = self.player_y - MINIMAP_RADIUS_TILES - 0.5
        base_tile_x = math.floor(world_origin_x)
        base_tile_y = math.floor(world_origin_y)
        sub_tile_x = world_origin_x - base_tile_x
        sub_tile_y = world_origin_y - base_tile_y
        self.canvas.create_rectangle(
            offset_x - 6,
            offset_y - 6,
            offset_x + minimap_px + 6,
            offset_y + minimap_px + 6,
            fill="#111111",
            outline="#bbbbbb",
        )

        for local_y in range(view_diameter + 1):
            for local_x in range(view_diameter + 1):
                world_x = base_tile_x + local_x
                world_y = base_tile_y + local_y
                if 0 <= world_y < len(self.map_layout) and 0 <= world_x < len(self.map_layout[0]):
                    tile = self.map_layout[world_y][world_x]
                else:
                    tile = "#"
                color = "#9a9a9a" if tile == "#" else "#1b1b1b"
                draw_x0 = offset_x + (local_x - sub_tile_x) * MINIMAP_SCALE
                draw_y0 = offset_y + (local_y - sub_tile_y) * MINIMAP_SCALE
                self.canvas.create_rectangle(
                    draw_x0,
                    draw_y0,
                    draw_x0 + MINIMAP_SCALE,
                    draw_y0 + MINIMAP_SCALE,
                    fill=color,
                    outline="#2a2a2a",
                )

        px = offset_x + (self.player_x - world_origin_x) * MINIMAP_SCALE
        py = offset_y + (self.player_y - world_origin_y) * MINIMAP_SCALE
        dx = math.cos(self.player_angle) * 12
        dy = math.sin(self.player_angle) * 12

        self.canvas.create_oval(px - 4, py - 4, px + 4, py + 4, fill="#ff7043", outline="")
        self.canvas.create_line(px, py, px + dx, py + dy, fill="#ffd166", width=2)

        for zombie in self.zombies:
            if not zombie["alive"]:
                continue

            dx_tiles = zombie["x"] - self.player_x
            dy_tiles = zombie["y"] - self.player_y
            if abs(dx_tiles) > MINIMAP_RADIUS_TILES + 0.5 or abs(dy_tiles) > MINIMAP_RADIUS_TILES + 0.5:
                continue
            zx = px + dx_tiles * MINIMAP_SCALE
            zy = py + dy_tiles * MINIMAP_SCALE
            color = "#7dff6d"
            if zombie["type"] == "runner":
                color = "#fff27d"
            if zombie["type"] == "brute":
                color = "#ff7d7d"
            self.canvas.create_oval(zx - 4, zy - 4, zx + 4, zy + 4, fill=color, outline="")

        for loot in self.loot_boxes:
            if loot.get("id") in self.collected_loot_ids:
                continue
            dx_tiles = loot["x"] - self.player_x
            dy_tiles = loot["y"] - self.player_y
            if abs(dx_tiles) > MINIMAP_RADIUS_TILES + 0.5 or abs(dy_tiles) > MINIMAP_RADIUS_TILES + 0.5:
                continue
            lx = px + dx_tiles * MINIMAP_SCALE
            ly = py + dy_tiles * MINIMAP_SCALE
            color = (
                "#7ed957" if loot["type"] == "food"
                else "#d7d7d7" if loot["type"] == "ammo"
                else "#cfb287" if loot["type"] == "materials"
                else "#7fd6ff"
            )
            self.canvas.create_rectangle(lx - 3, ly - 3, lx + 3, ly + 3, fill=color, outline="")

    def draw_full_map(self):
        map_width = len(self.map_layout[0])
        map_height = len(self.map_layout)
        max_panel_w = SCREEN_WIDTH - 120
        max_panel_h = SCREEN_HEIGHT - 120
        scale = min(max_panel_w / map_width, max_panel_h / map_height)
        scale = max(6, scale)
        panel_w = map_width * scale
        panel_h = map_height * scale
        x0 = (SCREEN_WIDTH - panel_w) / 2
        y0 = (SCREEN_HEIGHT - panel_h) / 2

        self.canvas.create_rectangle(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, fill="#000000", stipple="gray50", outline="")
        self.canvas.create_rectangle(x0 - 8, y0 - 8, x0 + panel_w + 8, y0 + panel_h + 8, fill="#11151a", outline="#e3e3e3", width=3)
        self.canvas.create_text(x0, y0 - 26, text="FULL MAP", anchor="sw", fill="#f4f4f4", font=("Courier", 22, "bold"))
        self.canvas.create_text(x0 + panel_w, y0 - 22, text="Press M or Esc to close", anchor="se", fill="#c6ced6", font=("Courier", 12, "bold"))

        for y, row in enumerate(self.map_layout):
            for x, tile in enumerate(row):
                color = "#8e959e" if tile == "#" else "#1b2229"
                self.canvas.create_rectangle(
                    x0 + x * scale,
                    y0 + y * scale,
                    x0 + (x + 1) * scale,
                    y0 + (y + 1) * scale,
                    fill=color,
                    outline="#29323a",
                )

        for loot in self.loot_boxes:
            if loot.get("id") in self.collected_loot_ids:
                continue
            lx = x0 + loot["x"] * scale
            ly = y0 + loot["y"] * scale
            color = (
                "#7ed957" if loot["type"] == "food"
                else "#d7d7d7" if loot["type"] == "ammo"
                else "#cfb287" if loot["type"] == "materials"
                else "#7fd6ff"
            )
            self.canvas.create_rectangle(lx - 2, ly - 2, lx + 2, ly + 2, fill=color, outline="")

        for zombie in self.zombies:
            if not zombie["alive"]:
                continue
            zx = x0 + zombie["x"] * scale
            zy = y0 + zombie["y"] * scale
            color = "#7dff6d"
            if zombie["type"] == "runner":
                color = "#fff27d"
            if zombie["type"] == "brute":
                color = "#ff7d7d"
            self.canvas.create_oval(zx - 3, zy - 3, zx + 3, zy + 3, fill=color, outline="")

        px = x0 + self.player_x * scale
        py = y0 + self.player_y * scale
        dx = math.cos(self.player_angle) * scale * 0.8
        dy = math.sin(self.player_angle) * scale * 0.8
        self.canvas.create_oval(px - 4, py - 4, px + 4, py + 4, fill="#ff7043", outline="")
        self.canvas.create_line(px, py, px + dx, py + dy, fill="#ffd166", width=2)

    def draw_weapon(self):
        gun = self.current_gun()
        if gun.get("melee"):
            center_x = SCREEN_WIDTH / 2
            bottom_y = SCREEN_HEIGHT + 10
            self.canvas.create_polygon(
                center_x - 40,
                bottom_y - 90,
                center_x - 8,
                bottom_y - 152,
                center_x + 18,
                bottom_y - 144,
                center_x - 10,
                bottom_y - 76,
                fill="#d8d8d8",
                outline="#181a1f",
                width=3,
            )
            self.canvas.create_polygon(
                center_x - 56,
                bottom_y - 38,
                center_x - 10,
                bottom_y - 84,
                center_x + 14,
                bottom_y - 34,
                center_x - 22,
                bottom_y + 12,
                fill="#5a4635",
                outline="#181a1f",
                width=3,
            )
            self.canvas.create_line(
                SCREEN_WIDTH / 2 - 10,
                HALF_HEIGHT,
                SCREEN_WIDTH / 2 + 10,
                HALF_HEIGHT,
                fill="#f4f4f4",
                width=2,
            )
            self.canvas.create_line(
                SCREEN_WIDTH / 2,
                HALF_HEIGHT - 10,
                SCREEN_WIDTH / 2,
                HALF_HEIGHT + 10,
                fill="#f4f4f4",
                width=2,
            )
            return

        gun_w = 220
        gun_h = 130
        center_x = SCREEN_WIDTH / 2
        bottom_y = SCREEN_HEIGHT + 18
        flash = self.muzzle_flash > 0

        self.canvas.create_polygon(
            center_x - gun_w / 2,
            bottom_y - gun_h * 0.35,
            center_x - gun_w * 0.20,
            bottom_y - gun_h,
            center_x + gun_w * 0.20,
            bottom_y - gun_h,
            center_x + gun_w / 2,
            bottom_y - gun_h * 0.35,
            center_x + gun_w * 0.28,
            bottom_y,
            center_x - gun_w * 0.28,
            bottom_y,
            fill=gun["color"],
            outline="#181a1f",
            width=3,
        )
        self.canvas.create_polygon(
            center_x - 46,
            bottom_y - gun_h - 62,
            center_x + 46,
            bottom_y - gun_h - 62,
            center_x + 26,
            bottom_y - gun_h * 0.20,
            center_x - 26,
            bottom_y - gun_h * 0.20,
            fill="#2c3038",
            outline="#181a1f",
            width=3,
        )
        self.canvas.create_rectangle(
            center_x - 18,
            bottom_y - gun_h - 102,
            center_x + 18,
            bottom_y - gun_h - 62,
            fill="#6f7686",
            outline="#181a1f",
        )
        self.canvas.create_line(
            center_x - gun_w * 0.26,
            bottom_y - gun_h * 0.34,
            center_x + gun_w * 0.26,
            bottom_y - gun_h * 0.34,
            fill="#9ba4b4",
            width=3,
        )
        self.canvas.create_line(
            center_x - gun_w * 0.16,
            bottom_y - gun_h * 0.56,
            center_x + gun_w * 0.16,
            bottom_y - gun_h * 0.56,
            fill="#21252d",
            width=2,
        )
        if flash:
            self.canvas.create_polygon(
                center_x,
                bottom_y - gun_h - 132,
                center_x - 34,
                bottom_y - gun_h - 66,
                center_x + 34,
                bottom_y - gun_h - 66,
                fill="#ffd166",
                outline="#fff1b8",
            )
            self.canvas.create_polygon(
                center_x,
                bottom_y - gun_h - 108,
                center_x - 18,
                bottom_y - gun_h - 70,
                center_x + 18,
                bottom_y - gun_h - 70,
                fill="#fff0a6",
                outline="",
            )

        self.canvas.create_line(
            SCREEN_WIDTH / 2 - 10,
            HALF_HEIGHT,
            SCREEN_WIDTH / 2 + 10,
            HALF_HEIGHT,
            fill="#f4f4f4",
            width=2,
        )
        self.canvas.create_line(
            SCREEN_WIDTH / 2,
            HALF_HEIGHT - 10,
            SCREEN_WIDTH / 2,
            HALF_HEIGHT + 10,
            fill="#f4f4f4",
            width=2,
        )

    def draw_inventory(self):
        self.inventory_buttons = {}
        x0, y0, x1, y1 = self.inventory_panel_rect()
        self.canvas.create_rectangle(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, fill="#000000", stipple="gray50", outline="")
        self.canvas.create_rectangle(x0, y0, x1, y1, fill="#15181d", outline="#e3e3e3", width=3)
        self.canvas.create_text(x0 + 24, y0 + 24, text="INVENTORY", anchor="nw", fill="#f4f4f4", font=("Courier", 24, "bold"))
        self.canvas.create_text(x1 - 24, y0 + 28, text="Drag items between slots. Press E or Esc to close.", anchor="ne", fill="#c6ced6", font=("Courier", 12, "bold"))

        eq_x0, eq_y0, eq_x1, eq_y1 = self.equipment_slot_rect()
        self.canvas.create_text(eq_x0, eq_y0 - 12, text="Equipped Weapon", anchor="sw", fill="#f4f4f4", font=("Courier", 12, "bold"))
        self.canvas.create_rectangle(eq_x0, eq_y0, eq_x1, eq_y1, fill="#20262f", outline="#d9eff4", width=2)
        equipped_item = self.make_item("gun", 1, self.gun_index)
        eq_main, eq_accent = self.item_colors(equipped_item)
        self.canvas.create_rectangle(eq_x0 + 8, eq_y0 + 8, eq_x1 - 8, eq_y1 - 8, fill=eq_main, outline="")
        self.canvas.create_rectangle(eq_x0 + 14, eq_y0 + 18, eq_x1 - 14, eq_y1 - 14, fill=eq_accent, outline="")
        self.canvas.create_text((eq_x0 + eq_x1) / 2, eq_y0 + 22, text=self.item_label(equipped_item), fill="#ffffff", font=("Courier", 10, "bold"))
        self.canvas.create_text((eq_x0 + eq_x1) / 2, eq_y1 - 18, text="Active", fill="#fff0b3", font=("Courier", 10, "bold"))

        for index in range(INVENTORY_SLOTS):
            sx0, sy0, sx1, sy1 = self.inventory_slot_rect(index)
            fill = "#232831" if index != self.selected_slot else "#31404f"
            self.canvas.create_rectangle(sx0, sy0, sx1, sy1, fill=fill, outline="#7c8794", width=2)
            item = self.inventory[index]
            if item is None:
                self.canvas.create_text((sx0 + sx1) / 2, sy0 + 12, text=str(index + 1), fill="#58626f", font=("Courier", 10, "bold"))
                continue

            main, accent = self.item_colors(item)
            self.canvas.create_rectangle(sx0 + 8, sy0 + 8, sx1 - 8, sy1 - 8, fill=main, outline="")
            self.canvas.create_rectangle(sx0 + 14, sy0 + 18, sx1 - 14, sy1 - 14, fill=accent, outline="")
            self.canvas.create_text((sx0 + sx1) / 2, sy0 + 22, text=self.item_label(item), fill="#ffffff", font=("Courier", 10, "bold"))
            if item["type"] == "gun":
                self.canvas.create_text((sx0 + sx1) / 2, sy1 - 18, text="Equipable", fill="#fff0b3", font=("Courier", 10, "bold"))
            else:
                self.canvas.create_text((sx0 + sx1) / 2, sy1 - 18, text=f"x{item['count']}", fill="#ffffff", font=("Courier", 12, "bold"))

        item = self.selected_item()
        info_x = x0 + 26
        info_y = y0 + 72 + INVENTORY_ROWS * (SLOT_SIZE + SLOT_GAP) + 18
        self.canvas.create_text(info_x, info_y, text="Selected", anchor="nw", fill="#f4f4f4", font=("Courier", 16, "bold"))
        if item is not None:
            self.canvas.create_text(info_x, info_y + 28, text=self.item_label(item), anchor="nw", fill="#fff0b3", font=("Courier", 14, "bold"))
            if item["type"] == "food":
                detail = f"Consumable: restores {item.get('heal', FOOD_HEAL)} HP"
            elif item["type"] == "ammo":
                detail = f"Use to add {item.get('ammo_gain', 20)} reserve ammo"
            elif item["type"] == "materials":
                detail = "Crafting resource for ammo and stronger guns"
            else:
                detail = "Drag or equip this gun into the weapon slot"
            self.canvas.create_text(info_x, info_y + 52, text=detail, anchor="nw", fill="#c6ced6", font=("Courier", 12, "bold"))

            button_x = info_x + 250
            button_y = info_y + 10
            actions = []
            if item["type"] == "food":
                actions.append(("use_food", "Eat Food"))
            if item["type"] == "ammo":
                actions.append(("use_ammo", "Store Ammo"))
            if item["type"] == "gun":
                actions.append(("equip_gun", "Equip To Slot"))
            if item["type"] == "materials":
                actions.append(("craft_ammo", "Craft Ammo Item (1->1)"))
                for gun_index in range(1, len(GUNS)):
                    if self.gun_index < gun_index and not self.has_gun_item(gun_index):
                        actions.append(("craft_gun_" + str(gun_index), f"Craft {GUNS[gun_index]['name']} ({GUNS[gun_index]['craft_cost']})"))

            button_width = 150
            button_gap = 12
            for idx, (action, label) in enumerate(actions):
                bx0 = button_x + idx * (button_width + button_gap)
                by0 = button_y
                bx1 = bx0 + button_width
                by1 = by0 + 38
                self.inventory_buttons[action] = (bx0, by0, bx1, by1)
                self.canvas.create_rectangle(bx0, by0, bx1, by1, fill="#2f6f7d", outline="#d9eff4", width=2)
                self.canvas.create_text((bx0 + bx1) / 2, (by0 + by1) / 2, text=label, fill="#ffffff", font=("Courier", 12, "bold"))

        parts_text = f"Ammo: {self.count_item_type('ammo')}  Materials: {self.count_item_type('materials')}  Food: {self.count_item_type('food')}"
        self.canvas.create_text(x0 + 26, y1 - 22, text=parts_text, anchor="sw", fill="#c6ced6", font=("Courier", 12, "bold"))

        if self.drag_item is not None:
            main, accent = self.item_colors(self.drag_item)
            dx0 = self.mouse_x - 34
            dy0 = self.mouse_y - 34
            self.canvas.create_rectangle(dx0, dy0, dx0 + 68, dy0 + 68, fill=main, outline="#ffffff", width=2)
            self.canvas.create_rectangle(dx0 + 10, dy0 + 14, dx0 + 58, dy0 + 56, fill=accent, outline="")
            self.canvas.create_text(dx0 + 34, dy0 + 18, text=self.item_label(self.drag_item), fill="#ffffff", font=("Courier", 8, "bold"))
            if self.drag_item["type"] != "gun":
                self.canvas.create_text(dx0 + 34, dy0 + 50, text=f"x{self.drag_item['count']}", fill="#ffffff", font=("Courier", 10, "bold"))

    def draw_pause_menu(self):
        self.pause_buttons = {}
        panel_w = 360
        panel_h = 280
        x0 = (SCREEN_WIDTH - panel_w) / 2
        y0 = (SCREEN_HEIGHT - panel_h) / 2
        x1 = x0 + panel_w
        y1 = y0 + panel_h

        self.canvas.create_rectangle(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, fill="#000000", stipple="gray50", outline="")
        self.canvas.create_rectangle(x0, y0, x1, y1, fill="#181c22", outline="#f4f4f4", width=3)
        self.canvas.create_text((x0 + x1) / 2, y0 + 34, text="PAUSED", fill="#f4f4f4", font=("Courier", 26, "bold"))
        self.canvas.create_text((x0 + x1) / 2, y0 + 62, text="Game paused. Save, load, or quit.", fill="#c6ced6", font=("Courier", 12, "bold"))

        buttons = [
            ("resume_game", "Resume"),
            ("save_game", "Save .dpy"),
            ("load_game", "Load .dpy"),
            ("quit_game", "Quit"),
        ]
        by = y0 + 96
        for action, label in buttons:
            bx0, by0, bx1, by1 = x0 + 84, by, x1 - 84, by + 40
            self.pause_buttons[action] = (bx0, by0, bx1, by1)
            fill = "#2f6f7d" if action != "quit_game" else "#8a3c3c"
            self.canvas.create_rectangle(bx0, by0, bx1, by1, fill=fill, outline="#d9eff4", width=2)
            self.canvas.create_text((bx0 + bx1) / 2, (by0 + by1) / 2, text=label, fill="#ffffff", font=("Courier", 13, "bold"))
            by += 48

    def draw_hud(self):
        hp_ratio = self.player_hp / PLAYER_MAX_HP
        hp_color = "#77dd77" if hp_ratio > 0.55 else "#ffd166" if hp_ratio > 0.25 else "#ff5c5c"
        living_zombies = sum(1 for zombie in self.zombies if zombie["alive"])
        gun = self.current_gun()

        self.canvas.create_text(
            SCREEN_WIDTH - 14,
            14,
            text="WASD move  |  Arrows turn  |  Space shoot  |  R reload  |  E inventory  |  M map  |  Esc pause",
            anchor="ne",
            fill="#f4f4f4",
            font=("Courier", 12, "bold"),
        )
        self.canvas.create_text(
            18,
            SCREEN_HEIGHT - 58,
            text=f"HP {self.player_hp:03d}",
            anchor="w",
            fill=hp_color,
            font=("Courier", 24, "bold"),
        )
        self.canvas.create_rectangle(18, SCREEN_HEIGHT - 36, 238, SCREEN_HEIGHT - 18, fill="#181818", outline="#f4f4f4")
        self.canvas.create_rectangle(
            20,
            SCREEN_HEIGHT - 34,
            20 + 216 * hp_ratio,
            SCREEN_HEIGHT - 20,
            fill=hp_color,
            outline="",
        )
        self.canvas.create_text(
            SCREEN_WIDTH - 18,
            SCREEN_HEIGHT - 26,
            text=f"ZOMBIES {living_zombies}  NEXT {self.spawn_timer:0.1f}s",
            anchor="e",
            fill="#9ff08c",
            font=("Courier", 18, "bold"),
        )
        self.canvas.create_text(
            SCREEN_WIDTH / 2,
            SCREEN_HEIGHT - 22,
            text="TECHNIPEN SURVIVAL",
            anchor="center",
            fill="#d7d9dd",
            font=("Courier", 16, "bold"),
        )
        self.canvas.create_text(
            18,
            18,
            text=f"AMMO ITEMS {self.count_item_type('ammo')}  FOOD {self.count_item_type('food')}  MAT {self.count_item_type('materials')}  GUN {gun['name']}",
            anchor="nw",
            fill="#f4f4f4",
            font=("Courier", 14, "bold"),
        )
        self.canvas.create_text(
            18,
            40,
            text=(
                f"{'AMMO ' + str(self.mag_ammo) + '/' + str(gun['magazine']) if not gun.get('melee') else 'MELEE'}  "
                f"RESERVE {self.reserve_ammo}  LEVEL {self.level_index} ({self.map_size_name})  "
                f"KILLS {self.kill_count % LEVEL_KILL_TARGET}/{LEVEL_KILL_TARGET}"
            ),
            anchor="nw",
            fill="#f4f4f4",
            font=("Courier", 14, "bold"),
        )
        if self.message_timer > 0.0:
            self.canvas.create_text(
                SCREEN_WIDTH / 2,
                28,
                text=self.message,
                anchor="n",
                fill="#fff0a6",
                font=("Courier", 14, "bold"),
            )

    def draw_game_over(self):
        self.death_buttons = {}
        self.canvas.create_rectangle(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, fill="#000000", stipple="gray50", outline="")
        self.canvas.create_text(
            SCREEN_WIDTH / 2,
            SCREEN_HEIGHT / 2 - 24,
            text="YOU DIED",
            fill="#ff5c5c",
            font=("Courier", 42, "bold"),
        )
        self.canvas.create_text(
            SCREEN_WIDTH / 2,
            SCREEN_HEIGHT / 2 + 16,
            text="Retry the run or load your last save",
            fill="#f4f4f4",
            font=("Courier", 16, "bold"),
        )

        retry_rect = (
            SCREEN_WIDTH / 2 - 140,
            SCREEN_HEIGHT / 2 + 52,
            SCREEN_WIDTH / 2 - 10,
            SCREEN_HEIGHT / 2 + 92,
        )
        load_rect = (
            SCREEN_WIDTH / 2 + 10,
            SCREEN_HEIGHT / 2 + 52,
            SCREEN_WIDTH / 2 + 140,
            SCREEN_HEIGHT / 2 + 92,
        )
        self.death_buttons["retry_run"] = retry_rect
        self.death_buttons["load_save"] = load_rect

        for rect, label, color in [
            (retry_rect, "Retry", "#2f6f7d"),
            (load_rect, "Load Save", "#5f5f8c"),
        ]:
            x0, y0, x1, y1 = rect
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="#d9eff4", width=2)
            self.canvas.create_text(
                (x0 + x1) / 2,
                (y0 + y1) / 2,
                text=label,
                fill="#ffffff",
                font=("Courier", 13, "bold"),
            )

    def loop(self):
        now = time.perf_counter()
        dt = min(now - self.last_time, 0.05)
        self.last_time = now
        self.clamp_reserve_ammo()

        if not self.inventory_open and not self.pause_menu_open and not self.map_view_open:
            self.update_player(dt)
            self.update_zombies(dt)
            self.collect_loot()
            self.muzzle_flash = max(0.0, self.muzzle_flash - dt)
            self.message_timer = max(0.0, self.message_timer - dt)
            if self.reload_timer > 0.0:
                self.reload_timer = max(0.0, self.reload_timer - dt)
                if self.reload_timer == 0.0:
                    self.finish_reload()

        self.canvas.delete("all")
        self.draw_background()
        self.draw_renderables()
        self.draw_minimap()
        self.draw_weapon()
        self.draw_hud()
        if self.inventory_open:
            self.draw_inventory()
        if self.pause_menu_open:
            self.draw_pause_menu()
        if self.map_view_open:
            self.draw_full_map()
        if self.game_over:
            self.draw_game_over()

        self.root.after(16, self.loop)


def main():
    root = tk.Tk()
    RaycasterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
