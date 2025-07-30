import time
import numpy as np
import sounddevice as sd
import soundfile as sf

SAMPLE_RATE       = 16000
THRESHOLD         = 0.005   # Lowered for better silence sensitivity
MIN_SILENCE_TIME  = 2    # Time of silence to auto-stop (in seconds)
MAX_RECORD_TIME   = 15      # Maximum record duration (seconds)

def record_audio(filename="input.wav"):
    print("🎙️ Recording... Speak now. Auto-stop after {:.1f}s of silence.".format(MIN_SILENCE_TIME))

    frames = []
    silence_start = None
    start_time = time.time()
    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1)

    stream.start()
    try:
        while True:
            data, _ = stream.read(int(SAMPLE_RATE * 0.1))  # Read in 0.1s chunks
            rms = np.sqrt(np.mean(np.square(data)))

            frames.append(data.copy())

            if rms < THRESHOLD:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start >= MIN_SILENCE_TIME:
                    break
            else:
                silence_start = None

            if time.time() - start_time >= MAX_RECORD_TIME:
                break

    finally:
        stream.stop()
        stream.close()

    audio = np.concatenate(frames, axis=0)
    if audio.size == 0:
        print("⚠️ No audio captured—try speaking louder.")
    else:
        sf.write(filename, audio, SAMPLE_RATE)
        print(f"✅ Recording saved to: {filename}")

