from TTS.api import TTS
import os

# Make sure the output directory exists
os.makedirs("output", exist_ok=True)

# Load XTTS model (on CPU to avoid VRAM pressure)
print("🔄 Loading XTTS model...")
tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
tts.to("cpu")

# Run synthesis using your reference clip
print("🎙️ Synthesizing Mike Boudet voice...")
tts.tts_to_file(
    text="This is Mike Boudet, and you're listening to Sword and Scale. Episode 200 begins now.",
    speaker_wav="samples/mike_boudet.wav",
    language="en",
    file_path="output/mike_test.wav"
)

print("✅ Done! File saved to output/mike_test.wav")
