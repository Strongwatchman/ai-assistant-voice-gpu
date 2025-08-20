# arc/stt_handler.py — Speech-to-Text using Whisper (faster-whisper)

from faster_whisper import WhisperModel
import os

model_size = "medium"
compute_type = "cuda" if os.environ.get("USE_CUDA", "1") == "1" else "int8"

print(f"🧠 Loading Whisper model ({model_size}, compute_type={compute_type})...")
whisper_model = WhisperModel(model_size, compute_type=compute_type)

def transcribe_speech(input_path="input.wav"):
    print(f"📝 Transcribing: {input_path}")
    segments, info = whisper_model.transcribe(input_path, beam_size=5)
    result = " ".join(segment.text.strip() for segment in segments)
    return result.strip()
