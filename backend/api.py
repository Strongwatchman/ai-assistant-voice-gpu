# backend/api.py
from __future__ import annotations
import os
import io
import json
import inspect
import shutil
import tempfile
import subprocess
from typing import Optional, Any, Callable, List

from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ── ARC imports
from arc.model_selector import list_active_keys, set_selected_key
from arc.model_registry import MODEL_CONFIGS
from arc.voice_selector import available_speakers
from arc.config import load_settings, save_settings

# LLM entry points
try:
    from arc.llm_handler import generate_response as arc_generate
except Exception:
    arc_generate = None
try:
    from arc.arc_core import route_prompt as arc_route_prompt
except Exception:
    arc_route_prompt = None

# STT entry points
try:
    import arc.stt_handler as stt_mod
except Exception:
    stt_mod = None
try:
    import arc.transcriber as trans_mod
except Exception:
    trans_mod = None

# TTS entry points (primary → fallbacks)
try:
    import arc.tts_adapter as tts_adapter  # preferred (XTTS wrapper returning bytes)
except Exception:
    tts_adapter = None
try:
    import arc.voice_handler as voice_mod   # may expose *bytes* APIs in your tree
except Exception:
    voice_mod = None
try:
    import arc.tts as tts_mod               # alternate module some repos provide
except Exception:
    tts_mod = None

app = FastAPI(title="ARC Web Bridge API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:5173", "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ────────────────────────────────────────────────────────────────────────────────
# Helpers

def _safe_ensure_dir(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def _persist_text(path: str, text: str) -> None:
    _safe_ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.strip() + "\n")

def _to_wav_16k_mono(src_path: str) -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise HTTPException(
            status_code=500,
            detail="ffmpeg is not installed; install with: sudo apt-get install -y ffmpeg",
        )
    fd, dst_path = tempfile.mkstemp(suffix=".wav"); os.close(fd)
    try:
        cmd = [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-i", src_path, "-ar", "16000", "-ac", "1", "-f", "wav", dst_path
        ]
        subprocess.run(cmd, check=True)
        return dst_path
    except subprocess.CalledProcessError as e:
        try: os.unlink(dst_path)
        except: pass
        raise HTTPException(status_code=500, detail=f"ffmpeg failed to convert audio: {e}")

def _wav_to_mp3_bytes(wav_path: str) -> bytes:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise HTTPException(status_code=500, detail="ffmpeg missing for MP3 conversion.")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as mp3f:
        mp3_path = mp3f.name
    try:
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
               "-i", wav_path, "-codec:a", "libmp3lame", "-b:a", "160k", mp3_path]
        subprocess.run(cmd, check=True)
        with open(mp3_path, "rb") as fh:
            return fh.read()
    finally:
        try: os.unlink(mp3_path)
        except: pass

def _call_transcriber(func: Callable[..., Any], path_or_bytes: Any, lang: Optional[str]) -> Optional[str]:
    try:
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        kwargs = {}
        args = []
        if params:
            args.append(path_or_bytes)
        else:
            return None
        if len(params) >= 2:
            name = params[1].name.lower()
            if name in ("language", "lang") and lang:
                args.append(lang)
        else:
            for p in params:
                n = p.name.lower()
                if n in ("language", "lang") and lang:
                    kwargs[n] = lang
                    break
        out = func(*args, **kwargs)
        if isinstance(out, tuple) and out:
            return str(out[0] or "")
        return str(out or "")
    except Exception as e:
        print(f"STT call failed for {getattr(func, '__name__', func)}: {e}")
        return None

def _normalize_bytes_result(out: Any) -> Optional[bytes]:
    if out is None:
        return None
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    if isinstance(out, str) and os.path.exists(out):
        with open(out, "rb") as fh:
            return fh.read()
    if isinstance(out, dict):
        for k in ("wav", "audio", "bytes", "data"):
            v = out.get(k)
            if isinstance(v, (bytes, bytearray)):
                return bytes(v)
        for k in ("path", "file", "filename"):
            v = out.get(k)
            if isinstance(v, str) and os.path.exists(v):
                with open(v, "rb") as fh:
                    return fh.read()
    return None

def _try_tts_calls(func: Callable[..., Any], text: str, voice: Optional[str], lang: Optional[str]) -> Optional[bytes]:
    """
    Be aggressive: try many combinations so we satisfy wrappers that hide params.
    """
    trials: List[dict] = []

    # positional combos
    if voice is not None and lang is not None:
        trials.append({"args": (text, voice, lang), "kwargs": {}})
    if voice is not None:
        trials.append({"args": (text, voice), "kwargs": {}})
    if lang is not None:
        trials.append({"args": (text, lang), "kwargs": {}})

    # keyword combos (common names)
    kw_langs = ["language", "lang"]
    kw_voices = ["voice", "speaker", "speaker_id", "spk", "name"]

    # both
    for kl in kw_langs:
        for kv in kw_voices:
            trials.append({"args": (text,), "kwargs": {kl: lang, kv: voice}})
    # language only
    for kl in kw_langs:
        trials.append({"args": (text,), "kwargs": {kl: lang}})
    # voice only
    for kv in kw_voices:
        trials.append({"args": (text,), "kwargs": {kv: voice}})

    # last resort
    trials.append({"args": (text,), "kwargs": {}})

    last_err = None
    for t in trials:
        try:
            out = func(*t["args"], **t["kwargs"])
            b = _normalize_bytes_result(out)
            if b:
                return b
        except Exception as e:
            last_err = e
            continue
    if last_err:
        print(f"TTS call variants exhausted; last error: {last_err}")
    return None

# ────────────────────────────────────────────────────────────────────────────────
# Health

@app.get("/health")
def health() -> dict:
    return {"ok": True}

# ────────────────────────────────────────────────────────────────────────────────
# Models & Voices

@app.get("/models")
def http_models() -> dict:
    keys = list_active_keys()
    items = []
    for k in keys:
        cfg = MODEL_CONFIGS.get(k, {}) or {}
        gguf = (cfg.get("path") or "").strip()
        pretty = gguf.rsplit("/", 1)[-1] if gguf else k
        items.append({"key": k, "name": pretty, "gguf": gguf})
    return {"models": items}

@app.get("/voices")
def http_voices() -> dict:
    return {"voices": available_speakers}

# ────────────────────────────────────────────────────────────────────────────────
# Server defaults

class SettingsIn(BaseModel):
    model: Optional[str] = None
    voice: Optional[str] = None
    sttLanguage: Optional[str] = None  # "auto" or "en"/"es"/...

@app.get("/settings")
def http_get_settings() -> dict:
    return load_settings()

def _apply_selected_model(model_key: Optional[str]) -> None:
    if model_key:
        try:
            set_selected_key(model_key)
        except Exception as e:
            print(f"⚠️ set_selected_key failed: {e}")

def _apply_selected_voice(voice_id: Optional[str]) -> None:
    """
    Remember chosen voice without calling ARC's set_current_voice (older ensure_dir).
    """
    if not voice_id:
        return
    os.environ["ARC_VOICE"] = voice_id
    try:
        cfg_dir = os.path.expanduser("~/.config/arc")
        os.makedirs(cfg_dir, exist_ok=True)
        with open(os.path.join(cfg_dir, "voice.txt"), "w", encoding="utf-8") as f:
            f.write(voice_id.strip() + "\n")
    except Exception as e:
        print(f"⚠️ local persist of voice failed: {e}")

@app.post("/settings")
def http_save_settings(s: SettingsIn) -> dict:
    cur = load_settings()
    if s.model is not None:
        cur["model"] = s.model
        _apply_selected_model(s.model)
    if s.voice is not None:
        cur["voice"] = s.voice
        _apply_selected_voice(s.voice)
    if s.sttLanguage is not None:
        cur["sttLanguage"] = s.sttLanguage
        os.environ["WHISPER_LANG"] = "" if s.sttLanguage == "auto" else s.sttLanguage
        if s.sttLanguage and s.sttLanguage != "auto":
            os.environ["ARC_TTS_LANG"] = s.sttLanguage
    save_settings(cur)
    return {"ok": True, **cur}

# ────────────────────────────────────────────────────────────────────────────────
# Chat

class ChatIn(BaseModel):
    text: str
    history: Optional[list] = None

@app.post("/chat")
async def chat(req: Request, body: ChatIn) -> dict:
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Missing 'text'.")

    hdr_model = (req.headers.get("x-model") or "").strip()
    hdr_voice = (req.headers.get("x-voice") or "").strip()

    if hdr_model:
        _apply_selected_model(hdr_model)
    if hdr_voice:
        _apply_selected_voice(hdr_voice)

    try:
        if arc_generate:
            try:
                reply = arc_generate(text, history=body.history)  # type: ignore
            except TypeError:
                reply = arc_generate(text)  # type: ignore
        elif arc_route_prompt:
            reply = arc_route_prompt(text)  # type: ignore
        else:
            reply = f"(echo) {text}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")

    if isinstance(reply, (dict, list)):
        reply = json.dumps(reply, ensure_ascii=False)

    return {"text": str(reply)}

# ────────────────────────────────────────────────────────────────────────────────
# STT

@app.post("/stt")
async def stt(
    file: UploadFile | None = File(default=None),
    audio: UploadFile | None = File(default=None),
    audio_file: UploadFile | None = File(default=None),
    language: str | None = Form(default=None),
    prompt: str | None = Form(default=None),
) -> dict:
    up = file or audio or audio_file
    if not up:
        raise HTTPException(status_code=400, detail="No audio uploaded (file|audio|audio_file).")

    lang_env = (os.environ.get("WHISPER_LANG") or "").strip() or None
    lang = (language or lang_env) or None
    data = await up.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio upload.")

    raw_path = None
    wav_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as rawf:
            rawf.write(data); rawf.flush()
            raw_path = rawf.name

        wav_path = _to_wav_16k_mono(raw_path)

        if stt_mod and hasattr(stt_mod, "transcribe_file"):
            txt = _call_transcriber(stt_mod.transcribe_file, wav_path, lang)
            if txt is not None:
                return {"text": txt}

        if trans_mod and hasattr(trans_mod, "transcribe_file"):
            txt = _call_transcriber(trans_mod.transcribe_file, wav_path, lang)
            if txt is not None:
                return {"text": txt}

        if trans_mod and hasattr(trans_mod, "transcribe_bytes"):
            try:
                with open(wav_path, "rb") as fh:
                    b = fh.read()
                txt = _call_transcriber(trans_mod.transcribe_bytes, b, lang)  # type: ignore[arg-type]
                if txt is not None:
                    return {"text": txt}
            except Exception as e:
                print(f"transcribe_bytes failed: {e}")

        raise HTTPException(status_code=500, detail="No working transcriber found after conversion.")
    finally:
        if raw_path:
            try: os.unlink(raw_path)
            except: pass
        if wav_path:
            try: os.unlink(wav_path)
            except: pass

# ────────────────────────────────────────────────────────────────────────────────
# TTS (language-aware, robust argument passing)

class TTSIn(BaseModel):
    text: str
    voice: Optional[str] = None
    language: Optional[str] = None
    format: Optional[str] = "mp3"  # "mp3" or "wav"

def _synthesize_to_wav_bytes(text: str, voice: Optional[str], lang: Optional[str]) -> Optional[bytes]:
    """
    Order:
      1) arc.tts_adapter.*   (preferred)
      2) arc.voice_handler.* / arc.tts.*
      3) pyttsx3 fallback (if installed)
    We attempt many signatures so the `language` always reaches XTTS.
    """
    # 1) tts_adapter (most likely in your setup)
    if tts_adapter:
        for name in ("synthesize_bytes", "tts_bytes", "speak_bytes", "synthesize_wav", "speak_wav"):
            if hasattr(tts_adapter, name):
                b = _try_tts_calls(getattr(tts_adapter, name), text, voice, lang)
                if b:
                    return b

    # 2) voice_handler / tts
    for mod in (voice_mod, tts_mod):
        if not mod:
            continue
        for name in ("tts_bytes", "speak_bytes", "synthesize_bytes", "speak_wav", "synthesize_wav"):
            if hasattr(mod, name):
                b = _try_tts_calls(getattr(mod, name), text, voice, lang)
                if b:
                    return b

    # 3) pyttsx3 fallback (robotic, but keeps UX alive)
    try:
        import pyttsx3  # type: ignore
        engine = pyttsx3.init()
        try:
            if voice:
                for v in engine.getProperty("voices") or []:
                    if voice.lower() in (v.name or "").lower():
                        engine.setProperty("voice", v.id)
                        break
        except Exception:
            pass
        fd, out_wav = tempfile.mkstemp(suffix=".wav"); os.close(fd)
        try:
            engine.save_to_file(text, out_wav)
            engine.runAndWait()
            with open(out_wav, "rb") as fh:
                return fh.read()
        finally:
            try: os.unlink(out_wav)
            except: pass
    except Exception as e:
        print(f"pyttsx3 fallback failed: {e}")

    return None

@app.post("/tts")
async def tts(req: Request, body: TTSIn):
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Missing 'text'.")

    hdr_voice = (req.headers.get("x-voice") or "").strip()
    voice = (body.voice or "").strip() or hdr_voice or load_settings().get("voice") or os.environ.get("ARC_VOICE")
    if voice:
        _apply_selected_voice(voice)

    s = load_settings()
    lang = (body.language or "").strip().lower()
    if not lang:
        env_lang = (os.environ.get("ARC_TTS_LANG") or "").strip().lower()
        cfg_lang = (s.get("sttLanguage") or "").strip().lower()
        if cfg_lang == "auto":
            cfg_lang = ""
        whisper_lang = (os.environ.get("WHISPER_LANG") or "").strip().lower()
        lang = env_lang or cfg_lang or whisper_lang or "en"

    wav_bytes = _synthesize_to_wav_bytes(text, voice, lang)
    if not wav_bytes:
        raise HTTPException(
            status_code=500,
            detail=f"No working TTS backend found (voice='{voice or ''}', language='{lang}')."
        )

    fmt = (body.format or "mp3").lower()
    if fmt not in ("mp3", "wav"):
        fmt = "mp3"

    if fmt == "wav":
        return StreamingResponse(io.BytesIO(wav_bytes), media_type="audio/wav")

    fd, tmp_wav = tempfile.mkstemp(suffix=".wav"); os.close(fd)
    try:
        with open(tmp_wav, "wb") as fh:
            fh.write(wav_bytes)
        mp3 = _wav_to_mp3_bytes(tmp_wav)
    finally:
        try: os.unlink(tmp_wav)
        except: pass

    return StreamingResponse(io.BytesIO(mp3), media_type="audio/mpeg")

# ────────────────────────────────────────────────────────────────────────────────
# Interrupt

@app.post("/interrupt")
def interrupt() -> dict:
    return {"ok": True}

