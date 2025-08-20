# transcriber.py — Handles speech-to-text transcription using Whisper and dynamic GPU/CPU fallback

from faster_whisper import WhisperModel
from gpu_manager import auto_select_device, get_free_gpu_mem_mb
import torch
import gc

MODEL_SIZE = "medium"
AUDIO_PATH_DEFAULT = "input.wav"

DEVICE = auto_select_device()
print(f"[VRAM] Whisper init on {DEVICE} | Free: {get_free_gpu_mem_mb():.2f} MB")

try:
    compute_type = "float16" if DEVICE == "cuda" else "int8"
    model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=compute_type)
except Exception as e:
    print(f"[Transcriber] Falling back to CPU due to error: {e}")
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")

def clean_gpu_memory():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def transcribe(audio_path=AUDIO_PATH_DEFAULT):
    """Transcribe an audio file using WhisperModel."""
    print("🎙️ Transcribing...")
    print(f"[VRAM] Before ASR: {get_free_gpu_mem_mb():.2f} MB free")
    try:
        segments, _ = model.transcribe(audio_path, beam_size=5)
        transcription = " ".join(segment.text.strip() for segment in segments)
        return transcription.strip()
    except Exception as e:
        print(f"❌ Whisper transcription failed: {e}")
        return ""
    finally:
        clean_gpu_memory()
        print(f"[VRAM] After ASR: {get_free_gpu_mem_mb():.2f} MB free")

