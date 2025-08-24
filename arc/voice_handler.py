from __future__ import annotations

from pathlib import Path
import os
import re
import threading
import tempfile
from typing import List, Optional

# Minimal persistence helpers
from .voice_paths import VOICE_FILE, ensure_dir
# Direct XTTS loader (used for bytes-producing API)
from .xtts_loader import load_xtts_model

__all__ = [
    # selection & state
    "get_current_voice",
    "set_current_voice",
    "is_speaking",
    "stop",
    "speak",
    "speak_async",
    # bytes-producing API the backend looks for
    "synthesize_bytes",
    "tts_bytes",
    "speak_bytes",
    "synthesize_wav",
    "speak_wav",
    # optional
    "stop_playback",
]

# ────────────────────────────────────────────────────────────────────────────────
# Runtime toggles (env-driven)
# ────────────────────────────────────────────────────────────────────────────────
_STREAM_TTS = os.getenv("ARC_TTS_STREAM", "0") in ("1", "true", "True", "yes", "Y")
_SENTENCE_PAUSE_SEC = float(os.getenv("ARC_TTS_SENTENCE_PAUSE", "0.00"))
_MAX_CHARS = int(os.getenv("ARC_TTS_MAX_CHARS", "280"))

# ────────────────────────────────────────────────────────────────────────────────
# Voice resolution
# ────────────────────────────────────────────────────────────────────────────────
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
    """Persist selected voice and set ARC_VOICE for the running process."""
    v = (name or "").strip()
    if not v:
        return
    try:
        ensure_dir()  # ← correct usage (no args)
        VOICE_FILE.write_text(v + "\n", encoding="utf-8")
    except Exception as e:
        print(f"⚠️ Failed to persist voice to {VOICE_FILE}: {e}")
    os.environ["ARC_VOICE"] = v

# ────────────────────────────────────────────────────────────────────────────────
# Chunking helpers (streaming-by-sentence with soft wrapping)
# ────────────────────────────────────────────────────────────────────────────────
_SENTENCE_SPLIT = re.compile(r"(?<=[\.\!\?\:\;])\s+(?=[A-Z0-9])")

def _chunk_text(text: str, max_len: int = _MAX_CHARS) -> List[str]:
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

# ────────────────────────────────────────────────────────────────────────────────
# Playback engine with interrupt (uses tts_handler for your local speakers)
# ────────────────────────────────────────────────────────────────────────────────
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
    - Lazy-imports tts_handler to avoid circular import during module init.
    - If streaming is disabled, synthesize and play the entire text in one go.
    - If streaming is enabled, split into chunks; synth+play each; optional pauses between.
    """
    from .tts_handler import get_xtts_model, speak_xtts_multispeaker

    model = get_xtts_model()  # expected to be cached inside tts_handler
    device = getattr(model, "device", "cuda")
    print(f"🧠 [TTS] Using device for speech synthesis: {device} | speaker='{speaker}'")

    try:
        _set_speaking(True)
        _stop_tts.clear()

        if not _STREAM_TTS:
            msg = (text or "").strip()
            if not msg:
                return
            speak_xtts_multispeaker(msg, speaker=speaker, model=model)
            return

        chunks = _chunk_text(text)
        if not chunks:
            return

        print(f"[TTS] Streaming {len(chunks)} chunk(s) | pause={_SENTENCE_PAUSE_SEC:.2f}s | max_chars={_MAX_CHARS}")
        for i, chunk in enumerate(chunks, 1):
            if _stop_tts.is_set():
                print("🔕 TTS interrupted before next chunk.")
                break
            preview = (chunk.strip()[:120] + "…") if len(chunk) > 120 else chunk.strip()
            print(f"Text splitted to sentences. [{i}/{len(chunks)}] {preview!r}")
            speak_xtts_multispeaker(chunk, speaker=speaker, model=model)

            if _SENTENCE_PAUSE_SEC > 0 and i < len(chunks) and not _stop_tts.is_set():
                try:
                    remaining = _SENTENCE_PAUSE_SEC
                    while remaining > 0 and not _stop_tts.is_set():
                        sl = min(0.02, remaining)
                        remaining -= sl
                        threading.Event().wait(sl)
                except Exception:
                    pass

        if _stop_tts.is_set():
            _maybe_stop_backend()

    except Exception as e:
        print(f"🗣️ (TTS error): {e}")
    finally:
        _stop_tts.clear()
        _set_speaking(False)

def speak(text: str, voice: Optional[str] = None, *, block: bool = False) -> None:
    """Local playback (non-HTTP), same behavior as before."""
    global _speak_thread

    if is_speaking():
        stop()
        if _speak_thread and _speak_thread.is_alive():
            _speak_thread.join(timeout=1.0)

    spk = (voice or _current_voice()).strip()
    _speak_thread = threading.Thread(target=_speak_worker, args=(text, spk), daemon=True)
    _speak_thread.start()

    if block and _speak_thread.is_alive():
        _speak_thread.join()

def speak_async(text: str, voice: Optional[str] = None) -> None:
    speak(text, voice, block=False)

# ────────────────────────────────────────────────────────────────────────────────
# Bytes-producing API for FastAPI `/tts` (used by the webapp)
# ────────────────────────────────────────────────────────────────────────────────

_XTTS_BYTES_MODEL = None

def _get_bytes_model():
    global _XTTS_BYTES_MODEL
    if _XTTS_BYTES_MODEL is None:
        _XTTS_BYTES_MODEL = load_xtts_model()
    return _XTTS_BYTES_MODEL

def _resolve_lang(language: Optional[str]) -> str:
    if language and language.strip().lower() != "auto":
        return language.strip()
    for key in ("ARC_TTS_LANG", "WHISPER_LANG"):
        v = (os.environ.get(key) or "").strip()
        if v and v.lower() != "auto":
            return v
    return "en"

def _resolve_voice(voice: Optional[str]) -> str:
    v = (voice or os.environ.get("ARC_VOICE") or _current_voice()).strip()
    return v or _DEFAULT_VOICE

def synthesize_bytes(text: str, voice: Optional[str] = None, language: Optional[str] = None) -> bytes:
    """
    Generate **WAV bytes** using Coqui XTTS (multilingual). This is what the FastAPI
    backend probes for. We always forward `language` to avoid the “no language provided” error.
    """
    msg = (text or "").strip()
    if not msg:
        return b""

    spk = _resolve_voice(voice)
    lang = _resolve_lang(language)
    os.environ["ARC_TTS_LANG"] = lang  # helpful for any downstream adapter

    model = _get_bytes_model()
    fd, tmp_wav = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        model.tts_to_file(text=msg, speaker=spk, language=lang, file_path=tmp_wav)
        with open(tmp_wav, "rb") as fh:
            return fh.read()
    finally:
        try:
            os.unlink(tmp_wav)
        except Exception:
            pass

# Aliases the backend may try in order:
tts_bytes = synthesize_bytes
speak_bytes = synthesize_bytes
synthesize_wav = synthesize_bytes
speak_wav = synthesize_bytes

def stop_playback() -> None:
    """Optional hook if the backend calls into us on /interrupt."""
    pass

