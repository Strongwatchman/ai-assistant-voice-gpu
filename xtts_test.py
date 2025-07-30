from TTS.api import TTS
import os

# === CONFIGURATION ===
# Path to your Optimus Prime voice sample
OPTIMUS_WAV = "samples/optimus_prime.wav"

# Text to synthesize
TEXT = "Autobots, roll out. The fate of humanity depends on your courage."

# Output file path
OUTPUT_WAV = "output/optimus_output.wav"

# === RUN TTS ===
print("Loading XTTS model...")
tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)

# Ensure output directory exists
os.makedirs(os.path.dirname(OUTPUT_WAV), exist_ok=True)

print("Synthesizing...")
tts.tts_to_file(
    text=TEXT,
    speaker_wav=OPTIMUS_WAV,
    language="en",
    file_path=OUTPUT_WAV
)

print(f"✅ Done. Output saved to: {OUTPUT_WAV}")
