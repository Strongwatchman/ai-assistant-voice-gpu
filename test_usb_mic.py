import sounddevice as sd
import soundfile as sf

duration = 5  # seconds
samplerate = 44100
filename = "usb_mic_test.wav"
input_device = 7  # USB Mic device index

print(f"🎙️ Recording from device {input_device} for {duration} seconds...")
recording = sd.rec(int(samplerate * duration), samplerate=samplerate, channels=1, device=input_device)
sd.wait()
sf.write(filename, recording, samplerate)
print(f"✅ Saved to {filename}")
