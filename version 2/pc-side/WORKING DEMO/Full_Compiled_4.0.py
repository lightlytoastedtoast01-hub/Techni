import asyncio
import json
import math
import os
import platform
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import pygame
from difflib import get_close_matches

try:
    import tkinter as tk
    from tkinter import filedialog
except Exception:
    tk = None
    filedialog = None

try:
    from bleak import BleakClient, BleakScanner
except Exception:
    BleakClient = None
    BleakScanner = None

try:
    import sounddevice as sd
except Exception:
    sd = None

try:
    from vosk import KaldiRecognizer, Model
except Exception:
    KaldiRecognizer = None
    Model = None


BLE_MAC = "f2:4f:18:a6:f7:76"
DEVICE_NAME = "Arduino"
CHAR_UUID_X = "19B10001-E8F2-537E-4F6C-D104768A1214"
CHAR_UUID_Y = "19B10002-E8F2-537E-4F6C-D104768A1214"
CHAR_UUID_Z = "19B10003-E8F2-537E-4F6C-D104768A1214"
BLE_READ_INTERVAL = 0.05

DRAW_WINDOW_SIZE = (800, 600)
DEBUG_WINDOW_SIZE = (640, 500)
HEADER_HEIGHT = 110
MIN_DRAW_WINDOW_SIZE = (700, 420)
MIN_DEBUG_WINDOW_SIZE = (520, 420)
MAX_BRUSH_SIZE = 60

palette = [
    (0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 255, 0), (0, 0, 255),
    (255, 255, 0), (0, 255, 255), (255, 0, 255), (128, 0, 0), (0, 128, 0),
    (0, 0, 128), (128, 128, 0), (0, 128, 128), (128, 0, 128), (192, 192, 192),
    (128, 128, 128), (255, 165, 0), (255, 105, 180), (75, 0, 130), (0, 255, 127)
]

VOICE_COLOR_NAME_MAP = {
    "black": palette[0],
    "white": palette[1],
    "red": palette[2],
    "green": palette[3],
    "blue": palette[4],
    "yellow": palette[5],
    "cyan": palette[6],
    "aqua": palette[6],
    "magenta": palette[7],
    "maroon": palette[8],
    "dark green": palette[9],
    "navy": palette[10],
    "olive": palette[11],
    "teal": palette[12],
    "purple": palette[13],
    "silver": palette[14],
    "gray": palette[15],
    "grey": palette[15],
    "orange": palette[16],
    "pink": palette[17],
    "indigo": palette[18],
    "spring green": palette[19],
}

VOICE_COMMANDS = {
    "SET_BRUSH_SIZE": [
        "brush size",
        "set brush size",
        "make brush size",
        "set the brush size",
        "change brush size",
    ],
    "INCREASE_BRUSH_SIZE": [
        "increase brush size",
        "make the brush bigger",
        "make brush bigger",
        "bigger brush",
        "brush bigger",
        "raise brush size",
        "grow brush size",
    ],
    "DECREASE_BRUSH_SIZE": [
        "decrease brush size",
        "make the brush smaller",
        "make brush smaller",
        "smaller brush",
        "brush smaller",
        "lower brush size",
        "shrink brush size",
    ],
    "CHANGE_COLOR": [
        "change to",
        "change color to",
        "switch to",
        "switch color to",
        "set color to",
        "make it",
        "use",
    ],
    "FILL_SCREEN": [
        "fill screen",
        "fill the screen",
        "fill canvas",
        "fill the canvas",
        "phil screen",
        "phil the screen",
        "phil canvas",
        "phil the canvas",
        "pill screen",
        "pill the screen",
        "pill canvas",
        "pill the canvas",
        "will screen",
        "will the screen",
        "will canvas",
        "will the canvas",
        "paint the screen",
        "paint the canvas",
        "color the whole screen",
        "color the whole canvas",
    ],
    "UNDO": [
        "undo",
        "go back",
        "undo that",
    ],
    "REDO": [
        "redo",
        "redo that",
        "bring it back",
    ],
}

VOICE_SAMPLERATE = 16000
VOICE_BLOCKSIZE = 8000
VOICE_MIC_INDEX = 3
VOICE_COMMAND_TIMEOUT = 5

NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
}

NUMBER_WORD_ALIASES = {
    "to": "two",
    "too": "two",
    "for": "four",
    "fore": "four",
    "won": "one",
    "ate": "eight",
    "fory": "forty",
    "fourty": "forty",
    "sex": "six",
}

VOICE_WORD_ALIASES = {
    "said": "set",
    "says": "set",
    "so": "size",
    "sighs": "size",
    "brushes": "brush",
    "phil": "fill",
    "pill": "fill",
    "will": "fill",
    "filll": "fill",
}


def debug_log(message):
    print(message, flush=True)


def safe_write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def safe_read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def clamp_window_size(size, minimum):
    return max(size[0], minimum[0]), max(size[1], minimum[1])


def parse_number_words(text):
    cleaned = text.lower().replace("-", " ")
    tokens = [NUMBER_WORD_ALIASES.get(token, token) for token in cleaned.split() if token]
    if not tokens:
        return None
    if len(tokens) == 1 and tokens[0] in NUMBER_WORDS:
        return NUMBER_WORDS[tokens[0]]
    if len(tokens) == 2 and tokens[0] in ("twenty", "thirty", "forty", "fifty") and tokens[1] in NUMBER_WORDS:
        ones_value = NUMBER_WORDS[tokens[1]]
        if 0 <= ones_value <= 9:
            return NUMBER_WORDS[tokens[0]] + ones_value
    return None


def normalize_voice_text(text):
    cleaned = re.sub(r"[^a-z0-9 -]+", " ", text.lower()).replace("-", " ")
    tokens = [token for token in cleaned.split() if token]
    normalized_tokens = []
    for token in tokens:
        token = VOICE_WORD_ALIASES.get(token, token)
        token = NUMBER_WORD_ALIASES.get(token, token)
        normalized_tokens.append(token)
    return " ".join(normalized_tokens)


def merge_recognized_command(existing_text, new_text):
    existing_text = normalize_voice_text(existing_text)
    new_text = normalize_voice_text(new_text)
    if not existing_text:
        return new_text
    if not new_text:
        return existing_text
    if new_text == existing_text:
        return existing_text
    if new_text.startswith(existing_text):
        return new_text
    if existing_text.startswith(new_text):
        return existing_text

    existing_tokens = existing_text.split()
    new_tokens = new_text.split()
    max_overlap = min(len(existing_tokens), len(new_tokens))
    for overlap in range(max_overlap, 0, -1):
        if existing_tokens[-overlap:] == new_tokens[:overlap]:
            return " ".join(existing_tokens + new_tokens[overlap:])

    return " ".join(existing_tokens + new_tokens)


def detect_voice_intent(text):
    text = normalize_voice_text(text)

    brush_match = re.search(
        r"\b(?:brush size|set brush size|set the brush size|change brush size|make brush size)(?:\s+to)?\s+(\d{1,2})\b",
        text
    )
    if brush_match:
        size = max(1, min(MAX_BRUSH_SIZE, int(brush_match.group(1))))
        return {"intent": "SET_BRUSH_SIZE", "value": size}

    brush_words_match = re.search(
        r"\b(?:brush size|set brush size|set the brush size|change brush size|make brush size)(?:\s+to)?\s+([a-z -]+)\b",
        text
    )
    if brush_words_match:
        parsed_number = parse_number_words(brush_words_match.group(1).strip())
        if parsed_number is not None:
            size = max(1, min(MAX_BRUSH_SIZE, parsed_number))
            return {"intent": "SET_BRUSH_SIZE", "value": size}

    if any(phrase in text for phrase in VOICE_COMMANDS["INCREASE_BRUSH_SIZE"]):
        return {"intent": "INCREASE_BRUSH_SIZE"}

    if any(phrase in text for phrase in VOICE_COMMANDS["DECREASE_BRUSH_SIZE"]):
        return {"intent": "DECREASE_BRUSH_SIZE"}

    if any(phrase in text for phrase in VOICE_COMMANDS["FILL_SCREEN"]):
        return {"intent": "FILL_SCREEN"}

    if any(phrase in text for phrase in VOICE_COMMANDS["UNDO"]):
        return {"intent": "UNDO"}

    if any(phrase in text for phrase in VOICE_COMMANDS["REDO"]):
        return {"intent": "REDO"}

    color_match = re.search(
        r"\b(?:change (?:to|two|too)|change color (?:to|two|too)|switch (?:to|two|too)|switch color (?:to|two|too)|set color (?:to|two|too)|make it|use)\s+(.+)",
        text
    )
    if color_match:
        requested_color = color_match.group(1).strip()
        if requested_color in VOICE_COLOR_NAME_MAP:
            return {
                "intent": "CHANGE_COLOR",
                "color_name": requested_color,
                "color_rgb": VOICE_COLOR_NAME_MAP[requested_color],
            }
        color_names = list(VOICE_COLOR_NAME_MAP.keys())
        matches = get_close_matches(requested_color, color_names, n=1, cutoff=0.6)
        if matches:
            matched_color = matches[0]
            return {
                "intent": "CHANGE_COLOR",
                "color_name": matched_color,
                "color_rgb": VOICE_COLOR_NAME_MAP[matched_color],
            }

    all_phrases = [phrase for phrases in VOICE_COMMANDS.values() for phrase in phrases]
    matches = get_close_matches(text, all_phrases, n=1, cutoff=0.6)
    if matches:
        for intent, phrases in VOICE_COMMANDS.items():
            if matches[0] in phrases:
                if intent == "SET_BRUSH_SIZE":
                    return {"intent": "UNKNOWN"}
                return {"intent": intent}

    return {"intent": "UNKNOWN"}


def start_voice_thread(voice_state, command_queue):
    if sd is None or Model is None or KaldiRecognizer is None:
        voice_state["status"] = "Voice unavailable"
        voice_state["error"] = "Missing sounddevice or vosk"
        return

    script_dir = os.path.dirname(os.path.realpath(__file__))
    model_path = os.path.join(script_dir, "vosk-model-small-en-us-0.15")
    wakeword_list_path = os.path.join(script_dir, "wakewords.list")

    if not os.path.exists(model_path):
        voice_state["status"] = "Voice unavailable"
        voice_state["error"] = f"Missing model: {model_path}"
        return

    if not os.path.exists(wakeword_list_path):
        voice_state["status"] = "Voice unavailable"
        voice_state["error"] = f"Missing wakewords: {wakeword_list_path}"
        return

    wake_phrases = []
    with open(wakeword_list_path, "r", encoding="utf-8") as wake_file:
        for line in wake_file:
            line = line.strip()
            if not line:
                continue
            if '"' in line:
                first_quote = line.find('"')
                last_quote = line.rfind('"')
                if first_quote != -1 and last_quote > first_quote:
                    phrase = line[first_quote + 1:last_quote].strip()
                    if phrase:
                        wake_phrases.append(phrase)

    if not wake_phrases:
        voice_state["status"] = "Voice unavailable"
        voice_state["error"] = "No wake phrases found"
        return

    normalized_wake_phrases = {normalize_voice_text(phrase) for phrase in wake_phrases}

    def worker():
        audio_queue = queue.Queue()

        def callback(indata, frames, time_info, status):
            if status:
                voice_state["error"] = str(status)
            audio_queue.put(bytes(indata))

        try:
            voice_state["mic_index"] = VOICE_MIC_INDEX
            try:
                mic_info = sd.query_devices(VOICE_MIC_INDEX)
                voice_state["mic_name"] = mic_info.get("name", f"Mic {VOICE_MIC_INDEX}")
            except Exception as exc:
                voice_state["mic_name"] = f"Mic {VOICE_MIC_INDEX}"
                voice_state["error"] = f"Mic lookup failed: {exc}"

            voice_state["status"] = "Loading voice model..."
            model = Model(model_path)
            keyword_recognizer = KaldiRecognizer(model, VOICE_SAMPLERATE, json.dumps(wake_phrases))
            command_recognizer = KaldiRecognizer(model, VOICE_SAMPLERATE)
            listening_for_command = False
            current_command = ""
            last_progress_time = 0.0
            seen_cancel_nonce = voice_state.get("cancel_nonce", 0)
            voice_state["wakewords"] = ", ".join(wake_phrases)
            voice_state["status"] = f"Listening on mic {VOICE_MIC_INDEX}"

            def reset_command_session(status_message=None):
                nonlocal command_recognizer, listening_for_command, current_command, last_progress_time
                command_recognizer = KaldiRecognizer(model, VOICE_SAMPLERATE)
                listening_for_command = False
                current_command = ""
                last_progress_time = 0.0
                voice_state["partial"] = ""
                if status_message is None:
                    status_message = f"Listening on mic {VOICE_MIC_INDEX}"
                voice_state["status"] = status_message

            def trigger_wake_session(wake_text):
                nonlocal keyword_recognizer, listening_for_command, current_command, last_progress_time
                keyword_recognizer = KaldiRecognizer(model, VOICE_SAMPLERATE, json.dumps(wake_phrases))
                reset_command_session(f"Wake word detected on mic {VOICE_MIC_INDEX}")
                listening_for_command = True
                current_command = ""
                last_progress_time = time.time()
                voice_state["last_wakeword"] = wake_text
                voice_state["status"] = f"Wake word detected on mic {VOICE_MIC_INDEX}"

            with sd.RawInputStream(
                samplerate=VOICE_SAMPLERATE,
                blocksize=VOICE_BLOCKSIZE,
                dtype="int16",
                channels=1,
                callback=callback,
                device=VOICE_MIC_INDEX,
            ):
                while not voice_state["stop"]:
                    if voice_state.get("cancel_nonce", 0) != seen_cancel_nonce:
                        seen_cancel_nonce = voice_state.get("cancel_nonce", 0)
                        reset_command_session(f"Listening on mic {VOICE_MIC_INDEX}")
                        voice_state["last_intent"] = "Voice cancelled"

                    if listening_for_command and time.time() - last_progress_time > VOICE_COMMAND_TIMEOUT:
                        reset_command_session(f"Listening on mic {VOICE_MIC_INDEX}")
                        voice_state["last_intent"] = "Timed out waiting for command"

                    try:
                        data = audio_queue.get(timeout=0.2)
                    except queue.Empty:
                        continue

                    if keyword_recognizer.AcceptWaveform(data):
                        kw_result = json.loads(keyword_recognizer.Result())
                        kw_text = normalize_voice_text(kw_result.get("text", "").strip().lower())
                        if kw_text and any(phrase in kw_text for phrase in normalized_wake_phrases):
                            trigger_wake_session(kw_text)
                            continue

                    if not listening_for_command:
                        continue

                    if command_recognizer.AcceptWaveform(data):
                        result = json.loads(command_recognizer.Result())
                        text = result.get("text", "").strip().lower()
                        if text:
                            last_progress_time = time.time()
                            current_command = merge_recognized_command(current_command, text)
                            intent_data = detect_voice_intent(current_command)
                            voice_state["partial"] = current_command
                            if intent_data["intent"] != "UNKNOWN":
                                command_queue.put(intent_data)
                                voice_state["last_command"] = current_command
                                voice_state["last_intent"] = intent_data["intent"]
                                reset_command_session(f"Command queued: {intent_data['intent']}")
                    else:
                        partial = json.loads(command_recognizer.PartialResult())
                        partial_text = partial.get("partial", "").strip().lower()
                        if partial_text:
                            last_progress_time = time.time()
                            current_command = normalize_voice_text(partial_text)
                            voice_state["partial"] = current_command
                            voice_state["status"] = f"Listening for command on mic {VOICE_MIC_INDEX}"
        except Exception as exc:
            voice_state["status"] = "Voice error"
            voice_state["error"] = str(exc)

    threading.Thread(target=worker, daemon=True).start()


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


def prompt_png_path_tk():
    if tk is None or filedialog is None:
        return None

    root = tk.Tk()
    root.withdraw()
    if hasattr(root, "attributes"):
        root.attributes("-topmost", True)
    try:
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")],
            initialfile="drawing.png"
        )
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


def prompt_png_path_macos():
    chosen_path = run_osascript([
        'set chosenFile to choose file name with prompt "Export drawing as PNG" default name "drawing.png"',
        'POSIX path of chosenFile'
    ])
    if chosen_path is not None and chosen_path.suffix.lower() != ".png":
        chosen_path = chosen_path.with_suffix(".png")
    return chosen_path


def prompt_file_path(save_dialog):
    if platform.system() == "Darwin":
        return prompt_file_path_macos(save_dialog)
    return prompt_file_path_tk(save_dialog)


def prompt_png_path():
    if platform.system() == "Darwin":
        return prompt_png_path_macos()
    return prompt_png_path_tk()


def translate_action_list(action_list, y_offset):
    translated = []
    for action in action_list:
        if isinstance(action, dict) and action.get("type") == "fill":
            translated.append(dict(action))
        else:
            stroke, color, brush_size = action
            translated_points = [(x, y + y_offset) for x, y in stroke]
            translated.append((translated_points, color, brush_size))
    return translated


def serialize_action_list(action_list):
    serialized = []
    for action in action_list:
        if isinstance(action, dict) and action.get("type") == "fill":
            serialized.append({
                "type": "fill",
                "color": list(action["color"]),
            })
        else:
            stroke, color, brush_size = action
            serialized.append({
                "type": "stroke",
                "points": [[float(x), float(y)] for x, y in stroke],
                "color": list(color),
                "brush_size": brush_size,
            })
    return serialized


def deserialize_action_list(entries):
    actions = []
    for entry in entries:
        if entry.get("type") == "fill":
            actions.append({
                "type": "fill",
                "color": tuple(entry.get("color", [255, 255, 255])),
            })
            continue
        points = [tuple(point) for point in entry.get("points", [])]
        color = tuple(entry.get("color", [0, 0, 0]))
        brush_size = int(entry.get("brush_size", 6))
        if points:
            actions.append((points, color, max(1, min(MAX_BRUSH_SIZE, brush_size))))
    return actions


def catmull_rom(points, steps=8):
    if len(points) < 4:
        return points
    curve = []
    for i in range(1, len(points) - 2):
        p0 = points[i - 1]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[i + 2]
        for j in range(steps):
            t = j / steps
            t2 = t * t
            t3 = t2 * t
            x = 0.5 * (
                (2 * p1[0]) + (-p0[0] + p2[0]) * t +
                (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
            )
            y = 0.5 * (
                (2 * p1[1]) + (-p0[1] + p2[1]) * t +
                (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
            )
            curve.append((x, y))
    curve.append(points[-2])
    curve.append(points[-1])
    return curve


def draw_stroke(surface, points, color, brush_size):
    if len(points) < 2:
        return
    last_point = points[0]
    for x, y in points[1:]:
        pygame.draw.line(surface, color, last_point, (x, y), brush_size)
        pygame.draw.circle(surface, color, (int(x), int(y)), max(1, brush_size // 2))
        last_point = (x, y)


def render_strokes(surface, smooth_strokes, current_smooth, current_stroke_color, current_stroke_brush_size, clip_top=HEADER_HEIGHT):
    surface.fill((255, 255, 255))
    surface.set_clip(pygame.Rect(0, clip_top, surface.get_width(), surface.get_height() - clip_top))

    for action in smooth_strokes:
        if isinstance(action, dict) and action.get("type") == "fill":
            surface.fill(action["color"])
            continue
        stroke, color, brush_size = action
        if len(stroke) > 3:
            curve = catmull_rom(stroke, 10)
            draw_stroke(surface, curve, color, brush_size)

    if len(current_smooth) > 3:
        curve = catmull_rom(current_smooth, 10)
        draw_stroke(surface, curve, current_stroke_color, current_stroke_brush_size)

    surface.set_clip(None)


def draw_button(surface, rect, label, font):
    pygame.draw.rect(surface, (235, 235, 235), rect, border_radius=6)
    pygame.draw.rect(surface, (40, 40, 40), rect, 2, border_radius=6)
    text = font.render(label, True, (0, 0, 0))
    text_rect = text.get_rect(center=rect.center)
    surface.blit(text, text_rect)


def connect_ble_factory(ble_status_message, ble_data):
    async def connect_ble_device():
        if BleakClient is None or BleakScanner is None:
            raise RuntimeError("bleak is not installed")

        try:
            debug_log("[ble] Trying MAC address...")
            client = BleakClient(BLE_MAC)
            await client.connect()
            if client.is_connected:
                debug_log("[ble] Connected using MAC address")
                return client
        except Exception as exc:
            debug_log(f"[ble] MAC connection failed: {exc}")

        debug_log("[ble] Scanning for device by name...")
        devices = await BleakScanner.discover()
        for device in devices:
            if device.name == DEVICE_NAME:
                debug_log(f"[ble] Found device: {device}")
                client = BleakClient(device.address)
                await client.connect()
                return client

        raise RuntimeError("Device not found")

    def set_ble_status(message):
        ble_status_message["value"] = message
        debug_log(f"[ble] {message}")

    def update_ble_motion(x_value, y_value, z_value, dt):
        dx = x_value - ble_data["x"]
        dy = y_value - ble_data["y"]
        dz = z_value - ble_data["z"]
        ble_data["x"] = x_value
        ble_data["y"] = y_value
        ble_data["z"] = z_value
        ble_data["dx"] = dx
        ble_data["dy"] = dy
        ble_data["dz"] = dz
        ble_data["sample_dt"] = dt
        ble_data["net_acceleration"] = math.sqrt(dx * dx + dy * dy + dz * dz)

    async def ble_loop():
        while not ble_data["stop"]:
            try:
                set_ble_status("BLE optional: connecting...")
                client = await connect_ble_device()
                ble_data["connected"] = True
                set_ble_status("BLE optional: connected")

                async with client:
                    last_read_time = time.time()
                    while not ble_data["stop"]:
                        x_value = float((await client.read_gatt_char(CHAR_UUID_X)).decode())
                        y_value = float((await client.read_gatt_char(CHAR_UUID_Y)).decode())
                        z_value = float((await client.read_gatt_char(CHAR_UUID_Z)).decode())
                        now = time.time()
                        dt = now - last_read_time
                        last_read_time = now
                        update_ble_motion(x_value, y_value, z_value, dt)
                        await asyncio.sleep(BLE_READ_INTERVAL)
            except Exception as exc:
                ble_data["connected"] = False
                set_ble_status(f"BLE optional: not connected ({exc})")
                await asyncio.sleep(1.0)

    return ble_loop


def start_ble_thread(ble_status_message, ble_data):
    if BleakClient is None or BleakScanner is None:
        ble_status_message["value"] = "BLE optional: unavailable"
        return

    ble_loop = connect_ble_factory(ble_status_message, ble_data)

    def runner():
        asyncio.run(ble_loop())

    threading.Thread(target=runner, daemon=True).start()


def spawn_debug_window(state_path, control_path):
    return subprocess.Popen(
        [sys.executable, __file__, "--debug-window", str(state_path), str(control_path)]
    )


def debug_window_main(state_path, control_path):
    pygame.init()
    screen = pygame.display.set_mode(DEBUG_WINDOW_SIZE, pygame.RESIZABLE)
    pygame.display.set_caption("TechniPen Debug")
    clock = pygame.time.Clock()
    title_font = pygame.font.SysFont(None, 36)
    font = pygame.font.SysFont(None, 26)
    small_font = pygame.font.SysFont(None, 22)

    toggle_rect = pygame.Rect(25, 275, 120, 32)
    cancel_voice_rect = pygame.Rect(160, 275, 130, 32)
    slider_track_rect = pygame.Rect(170, 290, 300, 10)
    slider_handle_radius = 10
    dragging_slider = False

    control_state = {
        "accel_input_source": "debug",
        "debug_acceleration_value": 0.0,
        "voice_cancel_nonce": 0,
    }

    def write_controls():
        safe_write_json(control_path, control_state)

    write_controls()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                new_size = clamp_window_size((event.w, event.h), MIN_DEBUG_WINDOW_SIZE)
                screen = pygame.display.set_mode(new_size, pygame.RESIZABLE)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if toggle_rect.collidepoint(event.pos):
                    control_state["accel_input_source"] = (
                        "ble" if control_state["accel_input_source"] == "debug" else "debug"
                    )
                    write_controls()
                elif cancel_voice_rect.collidepoint(event.pos):
                    control_state["voice_cancel_nonce"] += 1
                    write_controls()
                elif slider_track_rect.inflate(0, 24).collidepoint(event.pos):
                    dragging_slider = True
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging_slider = False
            elif event.type == pygame.MOUSEMOTION and dragging_slider:
                x_pos = max(slider_track_rect.left, min(slider_track_rect.right, event.pos[0]))
                ratio = (x_pos - slider_track_rect.left) / slider_track_rect.width
                max_accel = max(0.0001, control_state.get("max_accel_for_smoothing", 1.0))
                control_state["debug_acceleration_value"] = ratio * max_accel
                write_controls()

        state = safe_read_json(state_path) or {}
        if state.get("shutdown"):
            running = False

        control_state["accel_input_source"] = state.get(
            "accel_input_source",
            control_state["accel_input_source"]
        )
        control_state["max_accel_for_smoothing"] = state.get("max_accel_for_smoothing", 1.0)

        panel_rect = pygame.Rect(15, 15, screen.get_width() - 30, screen.get_height() - 30)
        screen.fill((244, 247, 250))
        pygame.draw.rect(screen, (225, 232, 240), panel_rect, border_radius=14)
        pygame.draw.rect(screen, (70, 90, 110), panel_rect, 2, border_radius=14)

        texts = [
            ("TechniPen Debug", title_font, 30, 28),
            (f"BLE: {state.get('ble_status_message', 'Waiting...')}", font, 30, 75),
            (
                f"X:{state.get('x', 0.0):.4f}  Y:{state.get('y', 0.0):.4f}  Z:{state.get('z', 0.0):.4f}",
                font, 30, 110
            ),
            (
                f"dX:{state.get('dx', 0.0):.4f}  dY:{state.get('dy', 0.0):.4f}  dZ:{state.get('dz', 0.0):.4f}",
                font, 30, 145
            ),
            (f"Net Accel: {state.get('net_acceleration', 0.0):.6f}", font, 30, 180),
            (f"Smoothing Alpha: {state.get('dynamic_follow_alpha', 0.0):.4f}", font, 30, 215),
            (f"dt: {state.get('sample_dt', 0.0):.4f}s", small_font, 30, 247),
            (f"Voice: {state.get('voice_status', 'Waiting...')}", small_font, 30, 275),
            (f"Mic: {state.get('voice_mic_index', '-')}  {state.get('voice_mic_name', '-')}", small_font, 30, 300),
            (f"Wake: {state.get('voice_last_wakeword', '-')}", small_font, 30, 325),
            (f"Partial: {state.get('voice_partial', '-')}", small_font, 30, 350),
            (f"Cmd: {state.get('voice_last_command', '-')}", small_font, 30, 375),
            (f"Intent: {state.get('voice_last_intent', '-')}", small_font, 30, 400),
            (f"Error: {state.get('voice_error', '-')}", small_font, 30, 425),
            (f"Status: {state.get('status_message', 'Ready')}", small_font, 30, 450),
        ]

        for text, used_font, x_pos, y_pos in texts:
            screen.blit(used_font.render(text, True, (15, 20, 28)), (x_pos, y_pos))

        draw_button(screen, toggle_rect, f"Source: {control_state['accel_input_source'].upper()}", small_font)
        draw_button(screen, cancel_voice_rect, "Cancel Voice", small_font)

        max_accel = max(0.0001, state.get("max_accel_for_smoothing", 1.0))
        debug_value = control_state.get("debug_acceleration_value", 0.0)
        progress = max(0.0, min(1.0, debug_value / max_accel))
        handle_x = int(slider_track_rect.left + progress * slider_track_rect.width)
        handle_y = slider_track_rect.centery
        pygame.draw.rect(screen, (210, 215, 220), slider_track_rect, border_radius=5)
        pygame.draw.rect(screen, (90, 100, 110), slider_track_rect, 2, border_radius=5)
        pygame.draw.circle(screen, (50, 120, 220), (handle_x, handle_y), slider_handle_radius)
        pygame.draw.circle(screen, (20, 20, 20), (handle_x, handle_y), slider_handle_radius, 2)
        slider_label = small_font.render(
            f"Debug Accel: {debug_value:.3f} / {max_accel:.3f}",
            True,
            (15, 20, 28)
        )
        screen.blit(slider_label, (170, 260))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


def main():
    pygame.init()
    screen = pygame.display.set_mode(DRAW_WINDOW_SIZE, pygame.RESIZABLE)
    pygame.display.set_caption("TechniPen 3.0")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    save_button_rect = pygame.Rect(10, 40, 80, 30)
    save_as_button_rect = pygame.Rect(100, 40, 100, 30)
    load_button_rect = pygame.Rect(210, 40, 80, 30)
    export_png_button_rect = pygame.Rect(300, 40, 120, 30)
    fill_canvas_button_rect = pygame.Rect(430, 40, 120, 30)
    undo_button_rect = pygame.Rect(560, 40, 80, 30)
    redo_button_rect = pygame.Rect(650, 40, 80, 30)

    raw_strokes = []
    smooth_strokes = []
    redo_strokes = []
    current_raw = []
    current_smooth = []

    current_color = palette[0]
    current_stroke_color = current_color
    current_brush_size = 6
    current_stroke_brush_size = current_brush_size
    last_file_path = None
    status_message = "Ready"

    brush_x = None
    brush_y = None
    mouse_down = False
    running = True

    radius = 50
    follow = 0.15
    slow_factor = 0.25
    min_follow_alpha = 0.02
    max_accel_for_smoothing = 1.0

    control_state = {
        "accel_input_source": "debug",
        "debug_acceleration_value": 0.0,
        "voice_cancel_nonce": 0,
    }
    voice_command_queue = queue.Queue()
    voice_state = {
        "status": "Voice starting...",
        "error": "",
        "wakewords": "",
        "last_wakeword": "",
        "last_command": "",
        "last_intent": "",
        "partial": "",
        "cancel_nonce": 0,
        "stop": False,
    }

    ble_status_message = {
        "value": "BLE optional: starting..." if BleakClient and BleakScanner else "BLE optional: unavailable"
    }
    ble_data = {
        "x": 0.0,
        "y": 0.0,
        "z": 0.0,
        "dx": 0.0,
        "dy": 0.0,
        "dz": 0.0,
        "net_acceleration": 0.0,
        "sample_dt": 0.0,
        "connected": False,
        "stop": False,
    }

    state_path = Path(tempfile.gettempdir()) / f"technipen_debug_state_{os.getpid()}.json"
    control_path = Path(tempfile.gettempdir()) / f"technipen_debug_control_{os.getpid()}.json"
    debug_process = spawn_debug_window(state_path, control_path)

    def set_status(message):
        nonlocal status_message
        status_message = message
        debug_log(f"[status] {message}")

    def get_effective_net_acceleration():
        if control_state["accel_input_source"] == "ble":
            return ble_data["net_acceleration"]
        return control_state["debug_acceleration_value"]

    def get_dynamic_follow_alpha():
        accel_ratio = min(1.0, get_effective_net_acceleration() / max_accel_for_smoothing)
        return max(min_follow_alpha, follow * (1.0 - 0.85 * accel_ratio))

    def begin_stroke():
        nonlocal mouse_down, current_raw, current_smooth, brush_x, brush_y
        nonlocal current_stroke_color, current_stroke_brush_size
        mouse_down = True
        current_raw = []
        current_smooth = []
        brush_x, brush_y = None, None
        current_stroke_color = current_color[:]
        current_stroke_brush_size = current_brush_size
        set_status("Drawing")

    def end_stroke():
        nonlocal mouse_down, current_raw, current_smooth, brush_x, brush_y
        mouse_down = False
        if current_smooth:
            raw_strokes.append((current_raw[:], current_color))
            smooth_strokes.append((current_smooth[:], current_stroke_color, current_stroke_brush_size))
            redo_strokes.clear()
            set_status(f"Stroke count: {len(smooth_strokes)}")
        current_raw = []
        current_smooth = []
        brush_x, brush_y = None, None

    def read_controls():
        data = safe_read_json(control_path)
        if not data:
            return
        control_state["accel_input_source"] = data.get("accel_input_source", control_state["accel_input_source"])
        control_state["debug_acceleration_value"] = float(
            data.get("debug_acceleration_value", control_state["debug_acceleration_value"])
        )
        control_state["voice_cancel_nonce"] = int(
            data.get("voice_cancel_nonce", control_state["voice_cancel_nonce"])
        )
        if control_state["voice_cancel_nonce"] != voice_state["cancel_nonce"]:
            voice_state["cancel_nonce"] = control_state["voice_cancel_nonce"]
            voice_state["status"] = f"Voice cancelled on mic {VOICE_MIC_INDEX}"
            voice_state["partial"] = ""
            voice_state["last_intent"] = "Voice cancelled"

    def write_debug_state():
        safe_write_json(state_path, {
            "ble_status_message": ble_status_message["value"],
            "x": ble_data["x"],
            "y": ble_data["y"],
            "z": ble_data["z"],
            "dx": ble_data["dx"],
            "dy": ble_data["dy"],
            "dz": ble_data["dz"],
            "net_acceleration": ble_data["net_acceleration"],
            "sample_dt": ble_data["sample_dt"],
            "dynamic_follow_alpha": get_dynamic_follow_alpha(),
            "status_message": status_message,
            "accel_input_source": control_state["accel_input_source"],
            "debug_acceleration_value": control_state["debug_acceleration_value"],
            "max_accel_for_smoothing": max_accel_for_smoothing,
            "voice_status": voice_state["status"],
            "voice_mic_index": voice_state.get("mic_index", VOICE_MIC_INDEX),
            "voice_mic_name": voice_state.get("mic_name", ""),
            "voice_last_wakeword": voice_state["last_wakeword"],
            "voice_last_command": voice_state["last_command"],
            "voice_last_intent": voice_state["last_intent"],
            "voice_partial": voice_state["partial"],
            "voice_error": voice_state["error"],
            "shutdown": False,
        })

    def save_drawing(path):
        safe_write_json(path, {
            "format": "TechniPen",
            "version": 3,
            "strokes": serialize_action_list(translate_action_list(smooth_strokes, -HEADER_HEIGHT)),
            "redo_strokes": serialize_action_list(translate_action_list(redo_strokes, -HEADER_HEIGHT)),
        })
        set_status(f"Saved {path.name}")

    def load_drawing(path):
        nonlocal smooth_strokes, redo_strokes, raw_strokes, current_raw, current_smooth
        nonlocal mouse_down, brush_x, brush_y
        data = safe_read_json(path) or {}
        loaded_strokes = deserialize_action_list(data.get("strokes", []))
        loaded_redo_strokes = deserialize_action_list(data.get("redo_strokes", []))
        if data.get("version", 2) >= 3:
            smooth_strokes = translate_action_list(loaded_strokes, HEADER_HEIGHT)
            redo_strokes = translate_action_list(loaded_redo_strokes, HEADER_HEIGHT)
        else:
            smooth_strokes = loaded_strokes
            redo_strokes = loaded_redo_strokes
        raw_strokes = []
        current_raw = []
        current_smooth = []
        mouse_down = False
        brush_x, brush_y = None, None
        set_status(f"Loaded {path.name}")

    def open_save_dialog():
        nonlocal last_file_path
        chosen_path = last_file_path or prompt_file_path(save_dialog=True)
        if chosen_path is None:
            set_status("Save cancelled")
            return
        save_drawing(chosen_path)
        last_file_path = chosen_path

    def open_save_as_dialog():
        nonlocal last_file_path
        chosen_path = prompt_file_path(save_dialog=True)
        if chosen_path is None:
            set_status("Save As cancelled")
            return
        save_drawing(chosen_path)
        last_file_path = chosen_path

    def open_load_dialog():
        nonlocal last_file_path
        chosen_path = prompt_file_path(save_dialog=False)
        if chosen_path is None:
            set_status("Load cancelled")
            return
        load_drawing(chosen_path)
        last_file_path = chosen_path

    def export_png():
        chosen_path = prompt_png_path()
        if chosen_path is None:
            set_status("PNG export cancelled")
            return
        export_size = (screen.get_width(), screen.get_height() - HEADER_HEIGHT)
        export_surface = pygame.Surface(export_size)
        export_strokes = translate_action_list(smooth_strokes, -HEADER_HEIGHT)
        export_current_smooth = [(x, y - HEADER_HEIGHT) for x, y in current_smooth]
        render_strokes(
            export_surface,
            export_strokes,
            export_current_smooth,
            current_stroke_color,
            current_stroke_brush_size,
            clip_top=0
        )
        pygame.image.save(export_surface, str(chosen_path))
        set_status(f"Exported {chosen_path.name}")

    def fill_canvas():
        nonlocal smooth_strokes, redo_strokes
        smooth_strokes.append({
            "type": "fill",
            "color": current_color,
        })
        redo_strokes.clear()
        set_status("Canvas filled")

    def undo_stroke():
        if smooth_strokes:
            redo_strokes.append(smooth_strokes.pop())
            set_status("Undo")
        else:
            set_status("Nothing to undo")

    def redo_stroke():
        if redo_strokes:
            smooth_strokes.append(redo_strokes.pop())
            set_status("Redo")
        else:
            set_status("Nothing to redo")

    def apply_voice_command(command):
        nonlocal current_brush_size, current_color

        intent = command.get("intent", "UNKNOWN")
        if intent == "SET_BRUSH_SIZE":
            if "value" not in command:
                set_status("Voice brush size missing")
                voice_state["last_intent"] = "SET_BRUSH_SIZE missing value"
                voice_state["status"] = f"Listening on mic {VOICE_MIC_INDEX}"
                voice_state["partial"] = ""
                return
            current_brush_size = max(1, min(MAX_BRUSH_SIZE, int(command["value"])))
            set_status(f"Voice brush size: {current_brush_size}")
        elif intent == "INCREASE_BRUSH_SIZE":
            current_brush_size = min(MAX_BRUSH_SIZE, current_brush_size + 5)
            set_status(f"Voice brush size: {current_brush_size}")
        elif intent == "DECREASE_BRUSH_SIZE":
            current_brush_size = max(1, current_brush_size - 5)
            set_status(f"Voice brush size: {current_brush_size}")
        elif intent == "CHANGE_COLOR":
            current_color = tuple(command["color_rgb"])
            set_status(f"Voice color: {command['color_name']}")
        elif intent == "FILL_SCREEN":
            fill_canvas()
        elif intent == "UNDO":
            undo_stroke()
        elif intent == "REDO":
            redo_stroke()
        else:
            set_status("Voice command unknown")

        voice_state["status"] = f"Listening on mic {VOICE_MIC_INDEX}"
        voice_state["partial"] = ""

    start_voice_thread(voice_state, voice_command_queue)
    start_ble_thread(ble_status_message, ble_data)

    while running:
        read_controls()
        while True:
            try:
                command = voice_command_queue.get_nowait()
            except queue.Empty:
                break
            apply_voice_command(command)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                new_size = clamp_window_size((event.w, event.h), MIN_DRAW_WINDOW_SIZE)
                screen = pygame.display.set_mode(new_size, pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                mods = getattr(event, "mod", 0)
                shortcut_mod = mods & (pygame.KMOD_CTRL | pygame.KMOD_META)
                keys = [
                    pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5,
                    pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9, pygame.K_0,
                    pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r, pygame.K_t,
                    pygame.K_y, pygame.K_u, pygame.K_i, pygame.K_o, pygame.K_p
                ]
                if shortcut_mod and event.key == pygame.K_s:
                    if mods & pygame.KMOD_SHIFT:
                        open_save_as_dialog()
                    else:
                        open_save_dialog()
                elif shortcut_mod and event.key == pygame.K_o:
                    open_load_dialog()
                elif shortcut_mod and event.key == pygame.K_z:
                    undo_stroke()
                elif shortcut_mod and event.key == pygame.K_x:
                    redo_stroke()
                elif event.key in keys:
                    current_color = palette[keys.index(event.key)]
                elif event.key in (pygame.K_LEFTBRACKET, pygame.K_MINUS):
                    current_brush_size = max(1, current_brush_size - 1)
                elif event.key in (pygame.K_RIGHTBRACKET, pygame.K_EQUALS):
                    current_brush_size = min(MAX_BRUSH_SIZE, current_brush_size + 1)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if save_button_rect.collidepoint(event.pos):
                    open_save_dialog()
                    continue
                if save_as_button_rect.collidepoint(event.pos):
                    open_save_as_dialog()
                    continue
                if load_button_rect.collidepoint(event.pos):
                    open_load_dialog()
                    continue
                if export_png_button_rect.collidepoint(event.pos):
                    export_png()
                    continue
                if fill_canvas_button_rect.collidepoint(event.pos):
                    fill_canvas()
                    continue
                if undo_button_rect.collidepoint(event.pos):
                    undo_stroke()
                    continue
                if redo_button_rect.collidepoint(event.pos):
                    redo_stroke()
                    continue
                if event.pos[1] < HEADER_HEIGHT:
                    continue
                begin_stroke()
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                end_stroke()

        if mouse_down:
            raw_x, raw_y = pygame.mouse.get_pos()
            current_raw.append((raw_x, raw_y))
            dynamic_follow = get_dynamic_follow_alpha()

            if brush_x is None:
                brush_x, brush_y = raw_x, raw_y

            dx = raw_x - brush_x
            dy = raw_y - brush_y
            dist = math.hypot(dx, dy)

            if dist > radius:
                brush_x += dx * dynamic_follow
                brush_y += dy * dynamic_follow
            else:
                brush_x += dx * dynamic_follow * slow_factor
                brush_y += dy * dynamic_follow * slow_factor

            current_smooth.append((brush_x, brush_y))

        render_strokes(screen, smooth_strokes, current_smooth, current_stroke_color, current_stroke_brush_size)

        pygame.draw.rect(screen, (228, 232, 236), pygame.Rect(0, 0, screen.get_width(), HEADER_HEIGHT))
        pygame.draw.line(screen, (170, 176, 184), (0, HEADER_HEIGHT), (screen.get_width(), HEADER_HEIGHT), 2)

        margin = 10
        preview_center = (margin + 20, margin + 20)
        pygame.draw.circle(screen, current_color, preview_center, max(1, current_brush_size // 2))
        pygame.draw.circle(screen, (0, 0, 0), preview_center, max(1, current_brush_size // 2), 1)
        size_text = font.render(f"Size: {current_brush_size}", True, (0, 0, 0))
        screen.blit(size_text, (margin + 45, margin + 10))

        draw_button(screen, save_button_rect, "Save", font)
        draw_button(screen, save_as_button_rect, "Save As", font)
        draw_button(screen, load_button_rect, "Load", font)
        draw_button(screen, export_png_button_rect, "Export PNG", font)
        draw_button(screen, fill_canvas_button_rect, "Fill Canvas", font)
        draw_button(screen, undo_button_rect, "Undo", font)
        draw_button(screen, redo_button_rect, "Redo", font)

        if last_file_path is not None:
            file_text = font.render(last_file_path.name, True, (0, 0, 0))
            screen.blit(file_text, (margin, margin + 80))

        pygame.display.flip()
        clock.tick(240)
        write_debug_state()

    ble_data["stop"] = True
    voice_state["stop"] = True
    safe_write_json(state_path, {"shutdown": True})
    time.sleep(0.1)

    if debug_process.poll() is None:
        debug_process.terminate()

    for path in (state_path, control_path):
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    pygame.quit()


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--debug-window":
        debug_window_main(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        main()
