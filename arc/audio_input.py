# arc/audio_input.py — Mic recording with silence detection

import sounddevice as sd
import soundfile as sf
import numpy as np

SAMPLE_RATE = 16000
CHANNELS = 1
DURATION = 15  # Max recording length in seconds
SILENCE_THRESHOLD = 0.005
SILENCE_DURATION = 1.5  # Seconds of silence to auto-stop

def record_audio(filename="input.wav"):
    print("🎙️ Recording... Speak now. Auto-stop after silence.")

    buffer = []
    silent_samples = 0
    silence_limit = int(SILENCE_DURATION * SAMPLE_RATE)

    def callback(indata, frames, time_info, status):
        nonlocal silent_samples
        volume = np.linalg.norm(indata) * 10
        buffer.extend(indata.copy())
        silent_samples = silent_samples + frames if volume < SILENCE_THRESHOLD else 0

        if silent_samples > silence_limit:
            raise sd.CallbackStop

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback):
            sd.sleep(int(DURATION * 1000))
        print("✅ Recording ended.")
    except sd.CallbackStop:
        print("🛑 Silence detected. Stopping...")

    audio_np = np.array(buffer)
    sf.write(filename, audio_np, SAMPLE_RATE)
    print(f"💾 Saved to: {filename}")
