# backend/api.py
from __future__ import annotations
import os
import io
import re
import json
import inspect
import shutil
import tempfile
import subprocess
from typing import Optional, Any, Callable

from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ── ARC imports
from arc.model_selector import list_active_keys, set_selected_key
from arc.model_registry import MODEL_CONFIGS

# voices list and clone mapping from your repo
from arc.voice_selector import available_speakers, custom_voice_wavs  # <- we use this
try:
    from arc.voice_handler import set_current_voice as arc_set_current_voice  # (unused; upstream ensure_dir bug)
except Exception:
    arc_set_current_voice = None

from arc.config import load_settings, save_settings

# LLM & STT
try:
    from arc.llm_handler import generate_response as arc_generate
except Exception:
    arc_generate = None
try:
    from arc.arc_core import route_prompt as arc_route_prompt
except Exception:
    arc_route_prompt = None

try:
    import arc.stt_handler as stt_mod
except Exception:
    stt_mod = None
try:
    import arc.transcriber as trans_mod
except Exception:
    trans_mod = None

# Optional TTS wrappers (kept as fallbacks)
try:
    import arc.tts_adapter as tts_adapter
except Exception:
    tts_adapter = None
try:
    import arc.voice_handler as voice_mod
except Exception:
    voice_mod = None
try:
    import arc.tts as tts_mod
except Exception:
    tts_mod = None

# Direct Coqui XTTS (PRIMARY path)
try:
    from TTS.api import TTS as COQUI_TTS
except Exception:
    COQUI_TTS = None  # type: ignore

try:
    import torch  # for device selection
except Exception:
    torch = None  # type: ignore

COQUI_MODEL = None
COQUI_DEVICE = "cuda" if (torch and hasattr(torch, "cuda") and torch.cuda.is_available()) else "cpu"

# ────────────────────────────────────────────────────────────────────────────────
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
               "-i", wav_path, "-codec:a", "libmp3lame", "-b:a", "192k", mp3_path]
        subprocess.run(cmd, check=True)
        with open(mp3_path, "rb") as fh:
            return fh.read()
    finally:
        try: os.unlink(mp3_path)
        except: pass

def _slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return re.sub(r"_+", "_", s).strip("_")

def _norm_lang(code: Optional[str]) -> str:
    if not code or code.lower() == "auto":
        return "en"
    # reduce things like en-US -> en
    return code.split("-")[0].lower()

# ────────────────────────────────────────────────────────────────────────────────
# STT adaptor

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
        accepts_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)
        if len(params) >= 2 and params[1].name.lower() in ("language", "lang") and lang:
            args.append(lang)
        else:
            for p in params:
                n = p.name.lower()
                if n in ("language", "lang") and lang:
                    kwargs[n] = lang
                    break
            else:
                if accepts_kwargs and lang:
                    kwargs["language"] = lang
        out = func(*args, **kwargs)
        if isinstance(out, tuple) and out:
            return str(out[0] or "")
        return str(out or "")
    except Exception as e:
        print(f"STT call failed for {getattr(func, '__name__', func)}: {e}")
        return None

# ────────────────────────────────────────────────────────────────────────────────
# TTS — PRIMARY: Coqui XTTS directly

def _ensure_coqui_loaded():
    global COQUI_MODEL
    if COQUI_MODEL is not None:
        return
    if COQUI_TTS is None:
        return
    model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
    print(f"🔊 Loading Coqui XTTS on [{COQUI_DEVICE}] …")
    COQUI_MODEL = COQUI_TTS(model_name)
    try:
        COQUI_MODEL.to(COQUI_DEVICE)
    except Exception:
        # Some CPU-only builds ignore .to(); safe to continue
        pass

def _xtts_synthesize_wav_bytes(text: str, voice: Optional[str], language: str) -> Optional[bytes]:
    """
    Use Coqui XTTS directly. If 'voice' matches your multispeaker list,
    call with speaker=voice. If 'voice' is in custom_voice_wavs, call with speaker_wav=...
    Returns raw WAV bytes.
    """
    _ensure_coqui_loaded()
    if COQUI_MODEL is None:
        return None

    # Normalize language to short form like "en"
    lang = _norm_lang(language)

    # temp path for WAV
    fd, out_wav = tempfile.mkstemp(suffix=".wav"); os.close(fd)
    try:
        # Clone?
        if voice and voice in custom_voice_wavs:
            ref = custom_voice_wavs[voice]
            if not os.path.exists(ref):
                print(f"❌ Missing reference sample for clone: {ref}")
                return None
            COQUI_MODEL.tts_to_file(text=text, speaker_wav=ref, language=lang, file_path=out_wav)
        else:
            # Multispeaker
            spk = voice if (voice and voice in available_speakers) else None
            # If unknown voice, Coqui will still synthesize with default voice if speaker=None
            COQUI_MODEL.tts_to_file(text=text, speaker=spk, language=lang, file_path=out_wav)

        with open(out_wav, "rb") as fh:
            return fh.read()
    finally:
        try: os.unlink(out_wav)
        except: pass

# ────────────────────────────────────────────────────────────────────────────────
# TTS — FALLBACKS (adapter / voice_handler / tts / pyttsx3)

def _try_call_variants(f: Callable[..., Any], variants: list[tuple[tuple[Any, ...], dict]]) -> Optional[bytes]:
    for args, kwargs in variants:
        try:
            out = f(*args, **kwargs)
            if isinstance(out, (bytes, bytearray)):
                return bytes(out)
            if isinstance(out, str) and os.path.exists(out):
                with open(out, "rb") as fh:
                    return fh.read()
            if isinstance(out, dict):
                for k in ("wav", "audio", "bytes", "data"):
                    if k in out and isinstance(out[k], (bytes, bytearray)):
                        return bytes(out[k])
                for k in ("path", "file", "filename"):
                    if k in out and isinstance(out[k], str) and os.path.exists(out[k]):
                        with open(out[k], "rb") as fh:
                            return fh.read()
        except TypeError:
            continue
        except Exception as e:
            print(f"TTS call variant failed: {e}")
            continue
    return None

def _call_tts_bytes(func: Callable[..., Any], text: str, voice: Optional[str],
                    language: Optional[str], fmt: Optional[str]) -> Optional[bytes]:
    # Signature-driven attempt
    try:
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        pnames = [p.name.lower() for p in params]
        accepts_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)
        args: list[Any] = []
        kwargs: dict[str, Any] = {}
        v_val = voice or ""
        v_slug = _slug(v_val) if v_val else ""
        l_val = (language or "").strip()
        f_val = fmt or "wav"

        voice_keys = ("voice", "speaker", "speaker_id", "spk", "name")
        lang_keys  = ("language", "lang", "locale")
        fmt_keys   = ("format", "fmt", "output_format", "audio_format")

        for p in params:
            n = p.name.lower()
            if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                if n == "text": args.append(text); continue
                if n in voice_keys and v_val: args.append(v_val); continue
                if n in lang_keys and l_val: args.append(l_val); continue
                if n in fmt_keys and f_val: args.append(f_val); continue

        given_names = {params[i].name.lower() for i in range(min(len(args), len(params)))}
        for p in params:
            n = p.name.lower()
            if n in given_names: continue
            if p.kind in (inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                if n == "text": kwargs["text"] = text
                elif n in voice_keys and v_val: kwargs[n] = v_val
                elif n in lang_keys and l_val: kwargs[n] = l_val
                elif n in fmt_keys and f_val: kwargs[n] = f_val

        if accepts_kwargs:
            if v_val and "voice" not in kwargs and all(k not in given_names for k in voice_keys):
                kwargs["voice"] = v_val
                kwargs.setdefault("speaker", v_slug or v_val)
            if l_val and "language" not in kwargs and all(k not in given_names for k in lang_keys):
                kwargs["language"] = l_val
            if f_val and "format" not in kwargs and all(k not in given_names for k in fmt_keys):
                kwargs["format"] = f_val

        out = func(*args, **kwargs)
        if isinstance(out, (bytes, bytearray)):
            return bytes(out)
        if isinstance(out, str) and os.path.exists(out):
            with open(out, "rb") as fh:
                return fh.read()
        if isinstance(out, dict):
            for k in ("wav", "audio", "bytes", "data"):
                if k in out and isinstance(out[k], (bytes, bytearray)):
                    return bytes(out[k])
            for k in ("path", "file", "filename"):
                if k in out and isinstance(out[k], str) and os.path.exists(out[k]):
                    with open(out[k], "rb") as fh:
                        return fh.read()
    except Exception as e:
        print(f"TTS call (signature path) failed: {e}")

    # Brute-force positional combos
    v_val = voice or ""
    v_slug = _slug(v_val) if v_val else ""
    l_val = (language or "").strip()
    combos = [
        ((text, v_val,   l_val), {}),
        ((text, v_slug,  l_val), {}),
        ((text, l_val,   v_val), {}),
        ((text, l_val,   v_slug), {}),
        ((text, v_val), {"language": l_val}),
        ((text, v_slug), {"language": l_val}),
        ((text,), {"voice": v_val, "language": l_val}),
        ((text,), {"speaker": v_slug or v_val, "language": l_val}),
        ((text,), {"language": l_val}),
    ]
    return _try_call_variants(func, combos)

def _synthesize_to_wav_bytes(text: str, voice: Optional[str], language: Optional[str]) -> Optional[bytes]:
    # 0) Coqui XTTS (direct)
    wav = _xtts_synthesize_wav_bytes(text, voice, _norm_lang(language or "en"))
    if wav:
        return wav

    # 1) arc.tts_adapter
    if tts_adapter and hasattr(tts_adapter, "synthesize_bytes"):
        try:
            b = _call_tts_bytes(tts_adapter.synthesize_bytes, text, voice, language or "en", "wav")
            if b:
                return b
        except Exception as e:
            print(f"tts_adapter failed: {e}")

    # 2) voice_handler
    if voice_mod:
        for name in ("tts_bytes", "speak_bytes", "synthesize_bytes", "speak_wav", "synthesize_wav"):
            if hasattr(voice_mod, name):
                b = _call_tts_bytes(getattr(voice_mod, name), text, voice, language or "en", "wav")
                if b:
                    return b

    # 3) tts module
    if tts_mod:
        for name in ("tts_bytes", "speak_bytes", "synthesize_bytes", "speak_wav", "synthesize_wav"):
            if hasattr(tts_mod, name):
                b = _call_tts_bytes(getattr(tts_mod, name), text, voice, language or "en", "wav")
                if b:
                    return b

    # 4) Optional pyttsx3 fallback (if present)
    try:
        import importlib.util
        if importlib.util.find_spec("pyttsx3") is not None:
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
# Settings

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

    hdr_model = req.headers.get("x-model")
    hdr_voice = req.headers.get("x-voice")
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

    lang = (language or os.environ.get("WHISPER_LANG") or "").strip() or None
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
# TTS

class TTSIn(BaseModel):
    text: str
    voice: Optional[str] = None
    language: Optional[str] = None
    format: Optional[str] = "mp3"  # "mp3" or "wav"

@app.post("/tts")
async def tts(req: Request, body: TTSIn):
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Missing 'text'.")

    # Voice from header > JSON > settings > env
    hdr_voice = req.headers.get("x-voice")
    voice = hdr_voice or (body.voice or "").strip() or load_settings().get("voice") or os.environ.get("ARC_VOICE")
    if voice:
        os.environ["ARC_VOICE"] = voice
        try:
            cfg_dir = os.path.expanduser("~/.config/arc")
            os.makedirs(cfg_dir, exist_ok=True)
            with open(os.path.join(cfg_dir, "voice.txt"), "w", encoding="utf-8") as f:
                f.write(voice.strip() + "\n")
        except Exception as e:
            print(f"⚠️ local persist of voice failed: {e}")

    # Language from header > JSON > saved settings > env > default 'en'
    hdr_lang = req.headers.get("x-language") or req.headers.get("x-lang")
    lang = (hdr_lang or (body.language or "").strip()
            or load_settings().get("sttLanguage")
            or os.environ.get("WHISPER_LANG") or "").strip()
    lang = _norm_lang(lang)

    # Try synth
    wav_bytes = _synthesize_to_wav_bytes(text, voice, lang)
    if not wav_bytes:
        raise HTTPException(status_code=501, detail="No server TTS available.")

    fmt = (body.format or "mp3").lower()
    if fmt not in ("mp3", "wav"):
        fmt = "mp3"

    if fmt == "wav":
        return StreamingResponse(io.BytesIO(wav_bytes), media_type="audio/wav")

    # WAV -> MP3
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

