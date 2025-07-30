import sounddevice as sd
import soundfile as sf

# Use a USB headset (you picked index 7 for both input and output)
input_device = 7
output_device = 7
samplerate = 48000  # Try 48000 instead of 44100
duration = 5  # seconds
filename = "test_usb_recording.wav"

print(f"\n🎙️ Recording for {duration} seconds at {samplerate} Hz...")
try:
    recording = sd.rec(
        int(duration * samplerate),
        samplerate=samplerate,
        channels=1,
        dtype='int16',
        device=input_device
    )
    sd.wait()
    sf.write(filename, recording, samplerate)
    print("✅ Recording complete. Now playing it back...")
    sd.play(recording, samplerate=samplerate, device=output_device)
    sd.wait()
    print("✅ Playback finished.")
except Exception as e:
    print(f"❌ Error: {e}")

