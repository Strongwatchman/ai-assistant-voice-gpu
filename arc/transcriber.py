# arc/transcriber.py

from faster_whisper import WhisperModel
import numpy as np
import os

# Force use of the RTX 2060 (GPU 1) by hiding the 3050 (GPU 0)
os.environ["CUDA_VISIBLE_DEVICES"] = "1"

WHISPER_MODEL_SIZE = "base"
USE_GPU = os.getenv("USE_GPU", "1") == "1"
COMPUTE_TYPE = "float16" if USE_GPU else "int8"

print(f"🧠 Initializing Whisper on {'cuda' if USE_GPU else 'cpu'} ({COMPUTE_TYPE})")

try:
    model = WhisperModel(
        WHISPER_MODEL_SIZE,
        device="cuda" if USE_GPU else "cpu",
        compute_type=COMPUTE_TYPE
    )
except Exception as e:
    print(f"❌ Failed to load Whisper model: {e}")
    raise

def transcribe(file_path="input.wav") -> str:
    print("🎙️ Transcribing...")

    segments, info = model.transcribe(file_path, beam_size=5)
    text_output = ""

    for segment in segments:
        text_output += segment.text.strip() + " "

    language = info.language
    confidence = info.language_probability
    print(f"🌐 Detected language: {language} ({confidence*100:.1f}%)")
    return text_output.strip()

