# arc/model_selector.py
from __future__ import annotations
import os
from pathlib import Path
from typing import List, Tuple, Optional

# Where models live
MODELS_DIR = Path(
    os.environ.get("LLM_MODELS_DIR",
                   Path(__file__).resolve().parents[1] / "llama.cpp" / "models")
).expanduser()

# Persist selection (backwards‑compatible)
SELECTED_FILE = Path(__file__).resolve().parent / "selected_model.txt"

# Registry of models (format, ctx, ngl, path, etc.)
from arc.model_registry import MODEL_CONFIGS

# Models we want to hide for now
DISABLED_KEYS = {"airoboros", "adventurous", "daybreak_q8", "stheno_q8", "specflash"}

# ---------- helpers ----------

def _resolve_path_from_cfg(cfg: dict) -> Optional[Path]:
    p = cfg.get("path")
    if not p:
        return None
    pp = Path(p)
    return (MODELS_DIR / pp) if not pp.is_absolute() else pp

def _active_models() -> List[Tuple[str, Path]]:
    """(key, gguf_path) for registry models that exist on disk and are not disabled."""
    out: List[Tuple[str, Path]] = []
    for k, cfg in MODEL_CONFIGS.items():
        if k == "default" or k in DISABLED_KEYS:
            continue
        gguf = _resolve_path_from_cfg(cfg)
        if gguf and gguf.exists():
            out.append((k, gguf))
    # deterministic order: keep registry order where possible
    return out

def _read_selected_raw() -> Optional[str]:
    if SELECTED_FILE.exists():
        try:
            val = SELECTED_FILE.read_text().strip()
            return val or None
        except Exception:
            return None
    return None

def _write_selected_raw(val: str) -> None:
    SELECTED_FILE.write_text(val)

def _env_override() -> Optional[str]:
    """Return a key or path from env, if provided."""
    v = os.getenv("ARC_MODEL")
    return v.strip() if v else None

# ---------- public API ----------

def get_selected_key() -> Optional[str]:
    """
    Return selected registry key if stored as a key (preferred).
    If the stored value is a path, try to map it back to a key.
    """
    env = _env_override()
    if env:
        # Allow key or path in env
        if env in MODEL_CONFIGS:
            return env
        p = Path(env)
        if p.exists():
            # try to find which key uses this path
            for k, cfg in MODEL_CONFIGS.items():
                gguf = _resolve_path_from_cfg(cfg)
                if gguf and gguf.resolve() == p.resolve():
                    return k
        # unknown env; fall through (will be treated as path later)

    raw = _read_selected_raw()
    if not raw:
        return None

    # If it's a key, return it
    if raw in MODEL_CONFIGS:
        return raw

    # If it's a path, try to map to a key
    p = Path(raw)
    if p.exists():
        for k, cfg in MODEL_CONFIGS.items():
            gguf = _resolve_path_from_cfg(cfg)
            if gguf and gguf.resolve() == p.resolve():
                return k
    return None

def get_selected_model() -> str:
    """
    Return the absolute GGUF path string for the selected model.
    Honors ARC_MODEL env, then saved key/path, else picks a sensible default.
    """
    # 1) Env override: key or path
    env = _env_override()
    if env:
        if env in MODEL_CONFIGS:
            cfg = MODEL_CONFIGS[env]
            gguf = _resolve_path_from_cfg(cfg)
            if gguf and gguf.exists():
                _write_selected_raw(env)  # persist as key
                return str(gguf)
        else:
            p = Path(env)
            if p.exists():
                _write_selected_raw(str(p))  # persist as path (unknown key)
                return str(p)

    # 2) Saved selection
    key = get_selected_key()
    if key and key in MODEL_CONFIGS:
        gguf = _resolve_path_from_cfg(MODEL_CONFIGS[key])
        if gguf and gguf.exists():
            return str(gguf)

    # 3) Fallback: prefer zephyr if present, else first active
    act = _active_models()
    if not act:
        raise FileNotFoundError(f"No GGUF models found under {MODELS_DIR}")

    # prefer zephyr if available
    for k, p in act:
        if k.lower() == "zephyr":
            _write_selected_raw(k)
            return str(p)

    # else first active
    k0, p0 = act[0]
    _write_selected_raw(k0)
    return str(p0)

def choose_model() -> None:
    """Interactive picker; persists selection (as key)."""
    act = _active_models()
    if not act:
        print(f"❌ No models found in {MODELS_DIR}")
        return

    print("\n🧠 Available models:")
    for i, (k, p) in enumerate(act, start=0):
        print(f"  [{i}] {k:<12s}  ({p.name})")

    # current
    curk = get_selected_key()
    if curk:
        print(f"\nCurrent: {curk}")

    raw = input("\nPick a model # (Enter to keep current): ").strip()
    if raw == "":
        # keep current or default to 0
        if curk:
            print(f"✅ Selected: {curk}")
            return
        pick_k, _ = act[0]
        _write_selected_raw(pick_k)
        print(f"✅ Selected: {pick_k}")
        return

    try:
        idx = int(raw)
    except Exception:
        print("Invalid input. No change.")
        return

    if not (0 <= idx < len(act)):
        print("Out of range. No change.")
        return

    pick_k, _ = act[idx]
    _write_selected_raw(pick_k)
    print(f"✅ Selected: {pick_k}")

# --- add to arc/model_selector.py ---

def list_active_keys() -> list[str]:
    """Public: keys that exist on disk and are not disabled."""
    try:
        return [k for (k, _p) in _active_models()]
    except Exception:
        return []

def set_selected_key(key: str) -> None:
    """Public: persist a registry key selection (if key is valid)."""
    if key in MODEL_CONFIGS:
        _write_selected_raw(key)

