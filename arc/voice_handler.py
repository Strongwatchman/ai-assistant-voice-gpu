from __future__ import annotations

from pathlib import Path
import os
import re
import threading
from typing import List, Optional

from .voice_paths import VOICE_FILE, ensure_dir

__all__ = [
    "get_current_voice",
    "set_current_voice",
    "speak",
    "speak_async",
    "stop",
    "is_speaking",
]

# ---------------------------------------------------------------------
# Voice resolution (same behavior)
# ---------------------------------------------------------------------

_DEFAULT_VOICE = "Abrahan Mack"
_CANDIDATES = [
    VOICE_FILE,
    (Path.home() / ".config" / "voice.txt"),
    (Path.home() / "AI_Assistant" / "arc" / "voice.txt"),
    (Path.home() / "AI_Assistant" / ".arc_voice"),
]

def _current_voice() -> str:
    env = os.environ.get("ARC_VOICE", "").strip()
    if env:
        print(f"🎚 Voice resolved from env ARC_VOICE: {env}")
        return env
    for fp in _CANDIDATES:
        try:
            if fp.exists():
                v = fp.read_text(encoding="utf-8").strip()
                if v:
                    print(f"🎚 Voice resolved from {fp}: {v}")
                    return v
        except Exception:
            pass
    print(f"🎚 Voice fallback to default: {_DEFAULT_VOICE}")
    return _DEFAULT_VOICE

def get_current_voice() -> str:
    return _current_voice()

def set_current_voice(name: str) -> None:
    try:
        ensure_dir(VOICE_FILE.parent)
        VOICE_FILE.write_text(name.strip(), encoding="utf-8")
    except Exception as e:
        print(f"⚠️ Failed to persist voice to {VOICE_FILE}: {e}")

# ---------------------------------------------------------------------
# Chunking helpers (streaming-by-sentence with soft wrapping)
# ---------------------------------------------------------------------

_SENTENCE_SPLIT = re.compile(r"(?<=[\.\!\?\:\;])\s+(?=[A-Z0-9])")

def _chunk_text(text: str, max_len: int = 280) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts: List[str] = []
    for sent in _SENTENCE_SPLIT.split(text):
        s = sent.strip()
        if not s:
            continue
        if len(s) <= max_len:
            parts.append(s)
        else:
            buf: List[str] = []
            cur = ""
            for w in s.split():
                if cur and len(cur) + 1 + len(w) > max_len:
                    buf.append(cur)
                    cur = w
                else:
                    cur = w if not cur else f"{cur} {w}"
            if cur:
                buf.append(cur)
            parts.extend(buf)
    return parts

# ---------------------------------------------------------------------
# Playback engine with interrupt
# ---------------------------------------------------------------------

_stop_tts = threading.Event()
_speak_thread: Optional[threading.Thread] = None
_speaking_lock = threading.Lock()
_is_speaking = False

def is_speaking() -> bool:
    with _speaking_lock:
        return _is_speaking

def _set_speaking(flag: bool) -> None:
    global _is_speaking
    with _speaking_lock:
        _is_speaking = flag

def stop() -> None:
    """Signal any ongoing speak() to stop as soon as a chunk finishes."""
    _stop_tts.set()

def _maybe_stop_backend():
    """Optional mid-chunk stop hook if your tts_handler exposes stop_playback()."""
    try:
        from .tts_handler import stop_playback  # optional
        stop_playback()
    except Exception:
        pass

def _speak_worker(text: str, speaker: str) -> None:
    """
    - Imports tts_handler lazily to avoid circular import during module init.
    - Splits text into chunks; for each chunk synth+play; checks stop() between chunks.
    """
    # Lazy import to prevent circular at import time
    from .tts_handler import get_xtts_model, speak_xtts_multispeaker

    model = get_xtts_model()  # expected to be cached inside tts_handler
    device = getattr(model, "device", "cuda")
    print(f"🧠 [TTS] Using device for speech synthesis: {device} | speaker='{speaker}'")

    try:
        _set_speaking(True)
        _stop_tts.clear()

        chunks = _chunk_text(text)
        if not chunks:
            return

        for i, chunk in enumerate(chunks, 1):
            if _stop_tts.is_set():
                print("🔕 TTS interrupted before next chunk.")
                break
            speak_xtts_multispeaker(chunk, speaker=speaker, model=model)

        if _stop_tts.is_set():
            _maybe_stop_backend()

    except Exception as e:
        print(f"🗣️ (TTS error): {e}")
    finally:
        _stop_tts.clear()
        _set_speaking(False)

# ---------------------------------------------------------------------
# Public API (keeps your existing signature)
# ---------------------------------------------------------------------

def speak(text: str, voice: Optional[str] = None, *, block: bool = False) -> None:
    """
    Speak `text` with optional `voice`.
    - Non-blocking by default; pass block=True if you need to wait.
    - If already speaking, we stop current playback first for immediate handover.
    """
    global _speak_thread

    if is_speaking():
        stop()
        if _speak_thread and _speak_thread.is_alive():
            _speak_thread.join(timeout=1.0)

    spk = (voice or _current_voice()).strip()
    _speak_thread = threading.Thread(target=_speak_worker, args=(text, spk), daemon=True)
    _speak_thread.start()

    if block:
        _speak_thread.join()

def speak_async(text: str, voice: Optional[str] = None) -> None:
    """Alias for speak(text, voice, block=False)."""
    speak(text, voice, block=False)

