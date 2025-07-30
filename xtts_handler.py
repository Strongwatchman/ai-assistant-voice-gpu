# xtts_handler.py

from TTS.api import TTS
import torch
import os

# Set your cloned reference voice path here
CLONE_REF_PATH = "samples/optimus_prime.wav"

# Load XTTS model once globally
print("🚀 Loading XTTS model...")
xtts_model = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
xtts_model.to("cuda" if torch.cuda.is_available() else "cpu")
print("✅ XTTS loaded.")

# Speaker setup (change this if you add toggling later)
use_xtts_clone = True  # default to cloning
current_voice = "Damien Black"

def speak_xtts(text: str):
    if use_xtts_clone:
        print(f"🎙️  Voice cloning from: {CLONE_REF_PATH}")
        xtts_model.tts_to_file(
            text=text,
            speaker_wav=CLONE_REF_PATH,
            file_path="output.wav"
        )
    else:
        print(f"🗣️  Speaking with multispeaker voice: {current_voice}")
        xtts_model.tts_to_file(
            text=text,
            speaker=current_voice,
            language="en",
            file_path="output.wav"
        )

    os.system("ffplay -autoexit -nodisp output.wav > /dev/null 2>&1")
