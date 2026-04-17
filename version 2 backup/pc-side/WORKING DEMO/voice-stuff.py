import os
import queue
import json
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from difflib import get_close_matches

# ==========================
# COMMANDS + SYNONYMS
# ==========================
COMMANDS = {
    "OPEN_BROWSER": ["open browser", "open browsing", "launch browser", "launch web", "google it", "browse web", "start browser", "open web"],
    "CLOSE_BROWSER": ["close browser", "exit browser", "quit browser", "shut down browser"],
    "PLAY_MUSIC": ["play music", "start music", "resume music", "turn on music"],
    "PAUSE_MUSIC": ["pause music", "stop music", "hold music"],
    "VOLUME_UP": ["volume up", "increase volume", "raise volume", "turn volume up", "louder", "crank volume"],
    "VOLUME_DOWN": ["volume down", "decrease volume", "lower volume", "turn volume down", "quieter"]
}

# ==========================
# DETECT INTENT
# ==========================
def detect_intent(text):
    text = text.lower()

    # Keyword + synonym match
    for intent, phrases in COMMANDS.items():
        for phrase in phrases:
            if all(word in text for word in phrase.split()):
                return intent

    # Fuzzy matching fallback
    all_phrases = [phrase for phrases in COMMANDS.values() for phrase in phrases]
    matches = get_close_matches(text, all_phrases, n=1, cutoff=0.6)
    if matches:
        for intent, phrases in COMMANDS.items():
            if matches[0] in phrases:
                return intent

    return "UNKNOWN"

# ==========================
# AUDIO CONFIG
# ==========================
samplerate = 16000
q = queue.Queue()

def callback(indata, frames, time, status):
    q.put(bytes(indata))

# ==========================
# MODEL PATH (auto-detect relative to script)
# ==========================
script_dir = os.path.dirname(os.path.realpath(__file__))
model_path = os.path.join(script_dir, "vosk-model-small-en-us-0.15")

if not os.path.exists(model_path):
    raise Exception(f"Model folder not found at {model_path}. Please download and unzip it here.")

model = Model(model_path)
recognizer = KaldiRecognizer(model, samplerate)

# ==========================
# SELECT MICROPHONE
# ==========================
# Use sd.query_devices() to find your mic index
mic_index = 3

# ==========================
# LIVE LISTENING LOOP
# ==========================
print("Listening... Speak now!")

with sd.RawInputStream(
        samplerate=samplerate,
        blocksize=8000,
        dtype='int16',
        channels=1,
        callback=callback,
        device=mic_index):
    
    while True:
        data = q.get()
        
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            text = result.get("text", "")
            if text:
                intent = detect_intent(text)
                print(f"Heard: {text}")
                print(f"Intent: {intent}")
                print("------------------")
        else:
            partial = json.loads(recognizer.PartialResult())
            if partial.get("partial", ""):
                # Optional: show partial results live
                print(f"Partial: {partial['partial']}")
