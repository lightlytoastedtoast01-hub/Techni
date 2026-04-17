import random
import tkinter as tk


TILE_SIZE = 8
MAP_WIDTH = 255
MAP_HEIGHT = 255
PIXEL_SCALE = 0.5

PALETTE = {
    "water_1": "#5ba7db",
    "water_2": "#3e86bf",
    "water_3": "#2c6798",
    "sand_1": "#e7d59c",
    "sand_2": "#d8c27e",
    "desert_1": "#e8cf77",
    "desert_2": "#d7b95a",
    "grass_1": "#8acb68",
    "grass_2": "#6fb34f",
    "tree_1": "#2d6b3f",
    "tree_2": "#1d4d2b",
    "taiga_1": "#7aa08b",
    "taiga_2": "#4d725f",
    "taiga_3": "#2f4d40",
    "hill_1": "#8f9b57",
    "hill_2": "#737d43",
    "mountain_1": "#8f8f8f",
    "mountain_2": "#666666",
    "mountain_3": "#d8d8d8",
}

TILE_PATTERNS = {
    "water": [
        "11122111",
        "11222211",
        "12233221",
        "22333322",
        "22333322",
        "12233221",
        "11222211",
        "11122111",
    ],
    "sand": [
        "11111111",
        "11112111",
        "11111111",
        "11111121",
        "11211111",
        "11111111",
        "11112111",
        "11111111",
    ],
    "grass": [
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
    ],
    "desert": [
        "11111111",
        "11121111",
        "11222111",
        "12222211",
        "11221111",
        "11111111",
        "11121111",
        "11111111",
    ],
    "trees": [
        "11111111",
        "11333111",
        "13344311",
        "33444431",
        "13444431",
        "11344311",
        "11133111",
        "11111111",
    ],
    "taiga": [
        "11131111",
        "11343111",
        "13454311",
        "11555511",
        "11354311",
        "11121111",
        "11121111",
        "11111111",
    ],
    "hills": [
        "11111111",
        "11122111",
        "11222211",
        "12222221",
        "12211221",
        "11211121",
        "11111111",
        "11111111",
    ],
    "mountains": [
        "11133111",
        "11344311",
        "13455431",
        "34555543",
        "45555554",
        "34544543",
        "13433431",
        "11311311",
    ],
}

PATTERN_COLORS = {
    "1": PALETTE["water_1"],
    "2": PALETTE["water_2"],
    "3": PALETTE["water_3"],
    "4": PALETTE["water_3"],
    "5": PALETTE["water_3"],
}


def clamp(value, low, high):
    return max(low, min(high, value))


def smooth_noise(width, height, seed, cell_size=5):
    rng = random.Random(seed)
    coarse_w = width // cell_size + 3
    coarse_h = height // cell_size + 3
    coarse = [[rng.random() for _ in range(coarse_w)] for _ in range(coarse_h)]
    field = []
    for y in range(height):
        row = []
        gy = y / cell_size
        y0 = int(gy)
        y1 = min(y0 + 1, coarse_h - 1)
        fy = gy - y0
        for x in range(width):
            gx = x / cell_size
            x0 = int(gx)
            x1 = min(x0 + 1, coarse_w - 1)
            fx = gx - x0
            top = coarse[y0][x0] * (1 - fx) + coarse[y0][x1] * fx
            bottom = coarse[y1][x0] * (1 - fx) + coarse[y1][x1] * fx
            row.append(top * (1 - fy) + bottom * fy)
        field.append(row)
    return field


def classify_tile(value, detail):
    if value < 0.36:
        return "water"
    if value < 0.43:
        return "sand"
    if value > 0.88:
        return "mountains"
    if value > 0.76:
        return "hills"
    if detail < 0.16:
        return "desert"
    if detail > 0.82:
        return "trees"
    if detail > 0.70:
        return "taiga"
    if detail > 0.62:
        return "trees"
    return "grass"


def pattern_colors_for(tile_name):
    if tile_name == "water":
        return {
            "1": PALETTE["water_1"],
            "2": PALETTE["water_2"],
            "3": PALETTE["water_3"],
            "4": PALETTE["water_3"],
            "5": PALETTE["water_3"],
        }
    if tile_name == "sand":
        return {
            "1": PALETTE["sand_1"],
            "2": PALETTE["sand_2"],
            "3": PALETTE["sand_2"],
            "4": PALETTE["sand_2"],
            "5": PALETTE["sand_2"],
        }
    if tile_name == "grass":
        return {
            "1": PALETTE["grass_1"],
            "2": PALETTE["grass_2"],
            "3": PALETTE["grass_2"],
            "4": PALETTE["grass_2"],
            "5": PALETTE["grass_2"],
        }
    if tile_name == "desert":
        return {
            "1": PALETTE["desert_1"],
            "2": PALETTE["desert_2"],
            "3": PALETTE["desert_2"],
            "4": PALETTE["desert_2"],
            "5": PALETTE["desert_2"],
        }
    if tile_name == "trees":
        return {
            "1": PALETTE["grass_1"],
            "2": PALETTE["grass_2"],
            "3": PALETTE["tree_1"],
            "4": PALETTE["tree_2"],
            "5": PALETTE["tree_2"],
        }
    if tile_name == "taiga":
        return {
            "1": PALETTE["taiga_1"],
            "2": PALETTE["taiga_2"],
            "3": PALETTE["taiga_2"],
            "4": PALETTE["taiga_3"],
            "5": PALETTE["taiga_3"],
        }
    if tile_name == "hills":
        return {
            "1": PALETTE["grass_1"],
            "2": PALETTE["hill_1"],
            "3": PALETTE["hill_2"],
            "4": PALETTE["hill_2"],
            "5": PALETTE["hill_2"],
        }
    return {
        "1": PALETTE["hill_1"],
        "2": PALETTE["mountain_1"],
        "3": PALETTE["mountain_3"],
        "4": PALETTE["mountain_2"],
        "5": PALETTE["mountain_2"],
    }


def generate_tile_map(width, height, seed=None):
    if seed is None:
        seed = random.randrange(1_000_000)
    elevation_noise = smooth_noise(width, height, seed, cell_size=7)
    moisture_noise = smooth_noise(width, height, seed + 97, cell_size=9)
    temperature_noise = smooth_noise(width, height, seed + 211, cell_size=11)

    tile_map = []
    for y in range(height):
        row = []
        for x in range(width):
            center_bias_x = abs(x - width / 2) / (width / 2)
            center_bias_y = abs(y - height / 2) / (height / 2)
            edge_falloff = (center_bias_x + center_bias_y) * 0.24
            elevation = clamp(elevation_noise[y][x] - edge_falloff, 0.0, 1.0)
            latitude_cooling = 1.0 - (y / max(1, height - 1)) * 0.55
            temperature = clamp(temperature_noise[y][x] * 0.50 + latitude_cooling * 0.40, 0.0, 1.0)
            moisture = clamp(moisture_noise[y][x] * 0.58 + temperature * 0.06, 0.0, 1.0)

            if 0.43 <= elevation <= 0.76:
                if temperature < 0.35 and moisture > 0.62:
                    row.append("taiga")
                    continue
                if temperature > 0.74 and moisture < 0.18:
                    row.append("desert")
                    continue

            row.append(classify_tile(elevation, moisture))
        tile_map.append(row)
    return seed, tile_map


class TerrainPreview:
    def __init__(self, root):
        self.root = root
        self.root.title("8x8 RPG Terrain Generator")
        self.root.configure(bg=PALETTE["grass_1"])

        self.seed_var = tk.StringVar()
        self.info_var = tk.StringVar()
        self.canvas = tk.Canvas(
            root,
            width=MAP_WIDTH * TILE_SIZE * PIXEL_SCALE,
            height=MAP_HEIGHT * TILE_SIZE * PIXEL_SCALE,
            bg=PALETTE["grass_1"],
            highlightthickness=0,
        )
        self.canvas.pack(padx=12, pady=(12, 8))

        controls = tk.Frame(root, bg=PALETTE["grass_1"])
        controls.pack(fill="x", padx=12, pady=(0, 12))

        tk.Button(
            controls,
            text="Generate New",
            command=self.generate,
            bg=PALETTE["tree_1"],
            fg="#f3f3f3",
            activebackground=PALETTE["tree_2"],
            activeforeground="#f3f3f3",
            relief="flat",
            padx=12,
            pady=6,
        ).pack(side="left")

        tk.Button(
            controls,
            text="Use Seed",
            command=self.generate_from_seed,
            bg=PALETTE["sand_2"],
            fg="#1f1f1f",
            activebackground=PALETTE["sand_1"],
            activeforeground="#1f1f1f",
            relief="flat",
            padx=12,
            pady=6,
        ).pack(side="left", padx=(8, 0))

        tk.Entry(
            controls,
            textvariable=self.seed_var,
            width=14,
            relief="flat",
            justify="center",
        ).pack(side="left", padx=(8, 0))

        tk.Label(
            controls,
            textvariable=self.info_var,
            bg=PALETTE["grass_1"],
            fg=PALETTE["tree_2"],
        ).pack(side="right")

        self.generate()

    def generate(self):
        seed, tile_map = generate_tile_map(MAP_WIDTH, MAP_HEIGHT)
        self.seed_var.set(str(seed))
        self.info_var.set(f"seed {seed}")
        self.draw(tile_map)

    def generate_from_seed(self):
        try:
            seed = int(self.seed_var.get())
        except ValueError:
            self.info_var.set("enter a whole-number seed")
            return
        seed, tile_map = generate_tile_map(MAP_WIDTH, MAP_HEIGHT, seed=seed)
        self.info_var.set(f"seed {seed}")
        self.draw(tile_map)

    def draw(self, tile_map):
        self.canvas.delete("all")
        for tile_y, row in enumerate(tile_map):
            for tile_x, tile_name in enumerate(row):
                pattern = TILE_PATTERNS[tile_name]
                tile_palette = pattern_colors_for(tile_name)
                for py, line in enumerate(pattern):
                    for px, char in enumerate(line):
                        color = tile_palette[char]
                        x0 = (tile_x * TILE_SIZE + px) * PIXEL_SCALE
                        y0 = (tile_y * TILE_SIZE + py) * PIXEL_SCALE
                        x1 = x0 + PIXEL_SCALE
                        y1 = y0 + PIXEL_SCALE
                        self.canvas.create_rectangle(
                            x0,
                            y0,
                            x1,
                            y1,
                            fill=color,
                            outline=color,
                        )


def main():
    root = tk.Tk()
    TerrainPreview(root)
    root.mainloop()


if __name__ == "__main__":
    main()
