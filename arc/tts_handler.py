# arc/tts_handler.py — Text-to-Speech engine using Coqui XTTS (single-shot, language-aware)

from __future__ import annotations

import contextlib
import os
import sys
from typing import Optional, List

import numpy as np
import sounddevice as sd
import torch
from TTS.api import TTS

# Your helper that maps a human-readable voice name to a reference wav/path.
# If it returns None, we fall back to passing the name via `speaker=...`.
from arc.state import get_current_speaker


# ---------------------------
# Console noise suppression
# ---------------------------
@contextlib.contextmanager
def suppress_output():
    with open(os.devnull, 'w') as fnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = fnull
        sys.stderr = fnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


# ---------------------------
# Global XTTS handle (cached)
# ---------------------------
_xtts_model: Optional[TTS] = None


def _pick_device() -> str:
    # Prefer CUDA:1 if present (you mentioned multi-GPU), else CUDA:0, else CPU.
    if torch.cuda.is_available():
        if torch.cuda.device_count() > 1:
            return "cuda:1"
        return "cuda"
    return "cpu"


def get_xtts_model() -> TTS:
    global _xtts_model
    if _xtts_model is None:
        device = _pick_device()
        print(f"🔊 Loading XTTS model on [{device}]...")
        with suppress_output():
            # Coqui XTTS v2 multilingual model
            _xtts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
            _xtts_model.to(device)
        print(f"🧠 [TTS Handler] Using device: {device}")
    return _xtts_model


# ---------------------------
# Helpers
# ---------------------------
def _default_lang() -> str:
    # Allow override: export ARC_TTS_LANG=de  (etc.)
    return os.getenv("ARC_TTS_LANG", "en").strip() or "en"


def _resolve_sample_rate(model: TTS) -> int:
    # Try a few common attributes; default to 24000 for XTTS if unknown.
    for attr in ("sample_rate", "output_sample_rate"):
        sr = getattr(model, attr, None)
        if isinstance(sr, (int, float)) and sr > 0:
            return int(sr)
    # Some versions tuck it under synthesizer
    try:
        sr = getattr(getattr(model, "synthesizer", None), "output_sample_rate", None)
        if isinstance(sr, (int, float)) and sr > 0:
            return int(sr)
    except Exception:
        pass
    return 24000


def _as_float32_mono(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    if arr.ndim == 2 and arr.shape[1] > 1:
        # average to mono if stereo/multichannel
        arr = np.mean(arr, axis=1).astype(np.float32)
    return arr.reshape(-1)


def stop_playback():
    """Hard stop current audio playback (used by 'U' toggle)."""
    try:
        sd.stop()
    except Exception:
        pass


# ---------------------------
# Public APIs
# ---------------------------
def speak_xtts_multispeaker(
    text: str,
    speaker: str,
    model: Optional[TTS] = None,
    sample_rate: Optional[int] = None,
    language: Optional[str] = None,
    **kwargs,
):
    """
    Single-shot playback:
    - Resolve speaker reference (voice sample path) via get_current_speaker(speaker)
    - Call XTTS once (or collect chunks if your API yields them)
    - Concatenate and play as *one* continuous block
    - Supply a language code (default 'en') to avoid multilingual errors
    """
    text = (text or "").strip()
    if not text:
        return

    model = model or get_xtts_model()
    lang = (language or _default_lang()).lower()
    sr = int(sample_rate or _resolve_sample_rate(model))

    # Try to resolve a reference wav for the chosen speaker
    # Expected: return a string path or None
    speaker_ref = None
    try:
        speaker_ref = get_current_speaker(speaker)  # path to a .wav (or None)
    except Exception:
        # If state lookup fails, we still try with `speaker=...`
        speaker_ref = None

    buffers: List[np.ndarray] = []

    # ---- XTTS synthesis (one-shot preferred) ----
    # Coqui XTTS v2 supports:
    #   wav = model.tts(text=..., speaker_wav="/path/to/ref.wav", language="en")
    # or, if no reference wav:
    #   wav = model.tts(text=..., speaker="SpeakerName", language="en")
    #
    # NOTE: If your version exposes a streaming generator, you can collect its chunks
    #       into `buffers` instead of playing them per-chunk.
    try:
        if speaker_ref and os.path.exists(speaker_ref):
            wav = model.tts(text=text, speaker_wav=speaker_ref, language=lang)
        else:
            # Fall back to passing the label; some setups embed known voices by name
            wav = model.tts(text=text, speaker=speaker, language=lang)
        buffers.append(_as_float32_mono(wav))
    except Exception as e:
        # If your backend has a stream API, adapt like this:
        # for chunk in model.tts_stream(text=text, speaker_wav=speaker_ref, language=lang):
        #     buffers.append(_as_float32_mono(chunk))
        # Remove the raise once a streaming path is wired (if desired).
        raise

    if not buffers:
        print("🗣️ (TTS: no audio generated)")
        return

    # Concatenate → gentle normalize to avoid clipping
    try:
        audio = np.concatenate(buffers, axis=0)
    except Exception:
        audio = np.hstack([b.reshape(-1) for b in buffers])

    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 1.0:
        audio = audio / (peak + 1e-6)

    # One continuous playback (voice_handler already threads this)
    sd.play(audio, sr)
    sd.wait()


def speak_xtts_clone(
    text: str,
    model: Optional[TTS] = None,
    speaker_wav: Optional[str] = None,
    language: Optional[str] = None,
    out_path: str = "/tmp/output.wav",
):
    """
    File-output clone helper (kept for parity with your previous code).
    """
    if model is None:
        model = get_xtts_model()
    if not speaker_wav:
        raise ValueError("❌ speaker_wav is required for cloned voice synthesis.")

    lang = (language or _default_lang()).lower()
    print(f"🗣️ [Voice Clone] {speaker_wav}: {text}")

    with suppress_output():
        model.tts_to_file(
            text=text,
            speaker_wav=speaker_wav,
            language=lang,
            file_path=out_path,
        )
    _play_output(out_path)


# ---------------------------
# Local playback from file
# ---------------------------
def _play_output(path: str):
    import subprocess
    try:
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
            check=False,
        )
    except Exception:
        # ffplay optional; silently ignore if missing
        pass

