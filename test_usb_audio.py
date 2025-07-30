import sounddevice as sd
import numpy as np

output_device = 7  # USB Speaker device index

fs = 44100
duration = 2.0
frequency = 440.0

print(f"🔊 Playing 440 Hz test tone to device {output_device}...")
samples = (np.sin(2 * np.pi * np.arange(fs * duration) * frequency / fs)).astype(np.float32)
sd.play(samples, samplerate=fs, device=output_device)
sd.wait()
print("✅ Done.")
