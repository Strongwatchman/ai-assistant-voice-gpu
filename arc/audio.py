# arc/audio.py

import sounddevice as sd
import soundfile as sf
import numpy as np
import time

SAMPLE_RATE = 16000
CHANNELS = 1
DURATION = 10  # Max recording length (seconds)
SILENCE_THRESHOLD = 0.007
SILENCE_DURATION = 1.2  # Seconds of silence to stop recording

def record_audio(filename="input.wav"):
    print("🎙️ Recording... Speak now. Auto-stop after silence.")

    buffer = []
    silent_samples = 0
    silence_limit = int(SILENCE_DURATION * SAMPLE_RATE)

    def callback(indata, frames, time_info, status):
        nonlocal silent_samples
        volume_norm = np.linalg.norm(indata) * 10
        buffer.extend(indata.copy())
        if volume_norm < SILENCE_THRESHOLD:
            silent_samples += frames
        else:
            silent_samples = 0

        if silent_samples >= silence_limit:
            raise sd.CallbackStop

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback):
            sd.sleep(int(DURATION * 1000))  # fallback max duration

        print("✅ Recording complete.")
    except sd.CallbackStop:
        print("🛑 Silence detected. Stopping...")

    audio_array = np.array(buffer)
    sf.write(filename, audio_array, SAMPLE_RATE)
    print(f"📁 Audio saved to: {filename}")
