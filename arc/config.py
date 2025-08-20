# arc/config.py

import json
from pathlib import Path

SETTINGS_FILE = Path("config/settings.json")

DEFAULT_SETTINGS = {
    "model": "zephyr-7b-alpha.Q4_K_M.gguf",
    "voice": "asya_anara",
    "input_mode": "mic",
    "ark_module": None
}

def load_settings():
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            print("⚠️ Failed to parse settings. Using defaults.")
    return DEFAULT_SETTINGS.copy()

def save_settings(settings: dict):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)
