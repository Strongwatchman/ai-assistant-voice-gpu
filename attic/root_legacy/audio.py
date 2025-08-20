# audio.py
import torchaudio
import soundfile as sf
import subprocess

AUDIO_PATH = "/tmp/output.wav"
SLOWED_AUDIO_PATH = "/tmp/output_slow.wav"

def save_audio(audio_tensor, sample_rate, path=AUDIO_PATH):
    """Save an audio tensor to a WAV file using torchaudio."""
    torchaudio.save(path, audio_tensor, sample_rate)

def load_audio(path=AUDIO_PATH):
    """Load audio from a WAV file as a tensor and sample rate."""
    return torchaudio.load(path)

def slow_audio(input_path=AUDIO_PATH, output_path=SLOWED_AUDIO_PATH, tempo=0.95):
    """Use ffmpeg to slow down audio playback."""
    subprocess.run(
        ["ffmpeg", "-y", "-i", input_path, "-filter:a", f"atempo={tempo}", output_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

def play_audio(path=SLOWED_AUDIO_PATH):
    """Play audio using ffplay."""
    subprocess.run(["ffplay", "-nodisp", "-autoexit", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def write_with_soundfile(audio_np, sample_rate, path=AUDIO_PATH):
    """Save audio with soundfile (e.g., from numpy or Whisper)."""
    sf.write(path, audio_np, sample_rate)
