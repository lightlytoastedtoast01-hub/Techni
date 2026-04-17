import os
import queue
import json
import re
import time
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from difflib import get_close_matches

# ==========================
# COMMANDS + SYNONYMS
# ==========================
COLOR_NAME_MAP = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "aqua": (0, 255, 255),
    "magenta": (255, 0, 255),
    "maroon": (128, 0, 0),
    "dark green": (0, 128, 0),
    "navy": (0, 0, 128),
    "olive": (128, 128, 0),
    "teal": (0, 128, 128),
    "purple": (128, 0, 128),
    "silver": (192, 192, 192),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "orange": (255, 165, 0),
    "pink": (255, 105, 180),
    "indigo": (75, 0, 130),
    "spring green": (0, 255, 127),
}

COMMANDS = {
    "SET_BRUSH_SIZE": [
        "brush size",
        "set brush size",
        "make brush size",
        "set the brush size",
        "change brush size"
    ],
    "INCREASE_BRUSH_SIZE": [
        "increase brush size",
        "make the brush bigger",
        "make brush bigger",
        "bigger brush",
        "brush bigger",
        "raise brush size",
        "grow brush size"
    ],
    "DECREASE_BRUSH_SIZE": [
        "decrease brush size",
        "make the brush smaller",
        "make brush smaller",
        "smaller brush",
        "brush smaller",
        "lower brush size",
        "shrink brush size"
    ],
    "CHANGE_COLOR": [
        "change to",
        "change color to",
        "switch to",
        "switch color to",
        "set color to",
        "make it",
        "use"
    ],
    "FILL_SCREEN": [
        "fill screen",
        "fill the screen",
        "fill canvas",
        "fill the canvas",
        "paint the screen",
        "paint the canvas",
        "color the whole screen",
        "color the whole canvas"
    ]
}

# ==========================
# INTENT DETECTION
# ==========================
def detect_intent(text: str) -> dict:
    text = text.lower().strip()

    brush_match = re.search(
        r"\b(?:brush size|set brush size|set the brush size|change brush size|make brush size)\s+(\d{1,2})\b",
        text
    )
    if brush_match:
        size = max(1, min(40, int(brush_match.group(1))))
        return {"intent": "SET_BRUSH_SIZE", "value": size}

    if any(phrase in text for phrase in COMMANDS["INCREASE_BRUSH_SIZE"]):
        return {"intent": "INCREASE_BRUSH_SIZE"}

    if any(phrase in text for phrase in COMMANDS["DECREASE_BRUSH_SIZE"]):
        return {"intent": "DECREASE_BRUSH_SIZE"}

    if any(phrase in text for phrase in COMMANDS["FILL_SCREEN"]):
        return {"intent": "FILL_SCREEN"}

    color_match = re.search(
        r"\b(?:change to|change color to|switch to|switch color to|set color to|make it|use)\s+(.+)",
        text
    )
    if color_match:
        requested_color = color_match.group(1).strip()
        if requested_color in COLOR_NAME_MAP:
            return {
                "intent": "CHANGE_COLOR",
                "color_name": requested_color,
                "color_rgb": COLOR_NAME_MAP[requested_color],
            }

        color_names = list(COLOR_NAME_MAP.keys())
        matches = get_close_matches(requested_color, color_names, n=1, cutoff=0.6)
        if matches:
            matched_color = matches[0]
            return {
                "intent": "CHANGE_COLOR",
                "color_name": matched_color,
                "color_rgb": COLOR_NAME_MAP[matched_color],
            }

    # Fuzzy matching fallback
    all_phrases = [phrase for phrases in COMMANDS.values() for phrase in phrases]
    matches = get_close_matches(text, all_phrases, n=1, cutoff=0.6)
    if matches:
        for intent, phrases in COMMANDS.items():
            if matches[0] in phrases:
                return {"intent": intent}

    return {"intent": "UNKNOWN"}

# ==========================
# AUDIO CONFIG
# ==========================
samplerate = 16000
blocksize = 8000
q = queue.Queue()

def callback(indata, frames, time_info, status):
    if status:
        print(f"Audio status: {status}")
    q.put(bytes(indata))

# ==========================
# MODEL PATH
# ==========================
script_dir = os.path.dirname(os.path.realpath(__file__))
model_path = os.path.join(script_dir, "vosk-model-small-en-us-0.15")

if not os.path.exists(model_path):
    raise FileNotFoundError(
        f"Model folder not found at {model_path}. "
        f"Download and unzip 'vosk-model-small-en-us-0.15' here."
    )

print(f"Loading Vosk model from: {model_path}")
model = Model(model_path)

# ==========================
# WAKEWORD LIST -> JSON ARRAY
# ==========================
wakeword_list_path = os.path.join(script_dir, "wakewords.list")
if not os.path.exists(wakeword_list_path):
    raise FileNotFoundError(
        f"wakewords.list not found at {wakeword_list_path}. "
        f"Create it and put your wake words there."
    )

wake_phrases = []
with open(wakeword_list_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        # Expect lines like: "hey pen" 1.5
        if '"' in line:
            first_quote = line.find('"')
            last_quote = line.rfind('"')
            if first_quote != -1 and last_quote > first_quote:
                phrase = line[first_quote + 1:last_quote].strip()
                if phrase:
                    wake_phrases.append(phrase)

if not wake_phrases:
    raise ValueError(
        "wakewords.list did not yield any phrases. "
        "Make sure lines look like: \"hey pen\" 1.5"
    )

wakewords_json = json.dumps(wake_phrases)
print("Using wake words:", wake_phrases)

# ==========================
# RECOGNIZERS
# ==========================
keyword_recognizer = KaldiRecognizer(model, samplerate, wakewords_json)
command_recognizer = KaldiRecognizer(model, samplerate)

# ==========================
# MICROPHONE INDEX
# ==========================
mic_index = 3

# ==========================
# STATE
# ==========================
listening_for_command = False
current_command = ""
last_speech_time = 0
COMMAND_TIMEOUT = 5  # seconds

print("======================================")
print(" Voice Assistant with Wake Word (Vosk)")
print("======================================")
print("Using microphone index:", mic_index)
print("Listening for wake word(s) from wakewords.list...")
print("After wake word is detected, speak your command.")
print("--------------------------------------")

# ==========================
# MAIN LOOP
# ==========================
def main():
    global listening_for_command, current_command, last_speech_time

    with sd.RawInputStream(
        samplerate=samplerate,
        blocksize=blocksize,
        dtype="int16",
        channels=1,
        callback=callback,
        device=mic_index
    ):
        while True:
            data = q.get()

            # ==========================
            # WAKE WORD MODE
            # ==========================
            if not listening_for_command:
                if keyword_recognizer.AcceptWaveform(data):
                    kw_result = json.loads(keyword_recognizer.Result())
                    kw_text = kw_result.get("text", "").strip().lower()
                    if kw_text:
                        print(f"[Wake] Detected: '{kw_text}'")
                        listening_for_command = True
                        current_command = ""
                        last_speech_time = time.time()
                        print("Wake word detected! Listening for your command...")
                continue

            # ==========================
            # COMMAND MODE
            # ==========================
            if command_recognizer.AcceptWaveform(data):
                result = json.loads(command_recognizer.Result())
                text = result.get("text", "").strip().lower()

                if text:
                    last_speech_time = time.time()

                    if current_command:
                        current_command += " " + text
                    else:
                        current_command = text

                    result = detect_intent(current_command)
                    intent = result["intent"]

                    if intent != "UNKNOWN":
                        print(f"[Command] Heard: {current_command}")
                        print(f"[Command] Intent: {intent}")
                        if "value" in result:
                            print(f"[Command] Brush size: {result['value']}")
                        if "color_name" in result:
                            print(f"[Command] Color: {result['color_name']} {result['color_rgb']}")
                        print("--------------------------------------")
                        listening_for_command = False
                        current_command = ""
                    else:
                        print(f"[Command] Unrecognized so far: '{current_command}'")

            else:
                partial = json.loads(command_recognizer.PartialResult())
                partial_text = partial.get("partial", "").strip().lower()

                if partial_text:
                    last_speech_time = time.time()
                    current_command = partial_text
                    print(f"[Partial command] {current_command}")

            # ==========================
            # TIMEOUT CHECK
            # ==========================
            if listening_for_command and time.time() - last_speech_time > COMMAND_TIMEOUT:
                print("[Timeout] No speech detected for "+str(COMMAND_TIMEOUT)+" seconds. Returning to wake mode.")
                listening_for_command = False
                current_command = ""

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting on user interrupt.")
