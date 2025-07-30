import sounddevice as sd
import soundfile as sf
import tempfile
import os
import torch
import gc
from state import get_current_speaker, get_xtts_model, get_use_xtts, get_xtts_ref_wav

def clean_gpu_memory_tts():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def speak_xtts(text: str):
    model = get_xtts_model()
    use_clone = get_use_xtts()
    speaker = get_current_speaker()
    ref_wav = get_xtts_ref_wav()

    try:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)

        if use_clone and ref_wav and os.path.exists(ref_wav):
            speak_xtts_clone(text, model, ref_wav)
        else:
            speak_xtts_multispeaker(text, speaker, model)
    except Exception as e:
        print(f"❌ [TTS] Error during speech: {e}")
    finally:
        clean_gpu_memory_tts()

def speak_xtts_multispeaker(text: str, speaker_name: str, model):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        model.tts_to_file(
            text=text,
            speaker=speaker_name,
            language="en",
            file_path=f.name
        )
        play_audio(f.name)

def speak_xtts_clone(text: str, model, ref_wav_path: str):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        model.tts_to_file(
            text=text,
            speaker_wav=ref_wav_path,
            language="en",
            file_path=f.name
        )
        play_audio(f.name)

def play_audio(path):
    audio, sr = sf.read(path, dtype="float32")
    print(f"🔊 Playing audio: {path}")
    print(f"   ├─ Sample rate: {sr}")
    print(f"   ├─ Duration: {len(audio) / sr:.2f} seconds")
    print(f"   ├─ Shape: {audio.shape}")
    print(f"   └─ Peak amplitude: {audio.max():.3f}")
    print(f"🧠 Sounddevice default output device: {sd.default.device}")
    print(f"🎧 Available output devices:")
    print(sd.query_devices())

    sd.play(audio, sr)
    sd.wait()
    os.remove(path)


