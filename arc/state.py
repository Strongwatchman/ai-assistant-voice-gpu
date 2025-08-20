# arc/state.py — Stores and manages assistant's dynamic state

from arc.xtts_loader import load_xtts_model

# Global voice settings
_current_speaker = "Sofia Hellen"
_use_xtts_clone = False
_xtts_ref_wav = None
_xtts_model = None  # Holds loaded XTTS model

# --- PyTorch 2.6 safe-unpickling for Coqui XTTS checkpoints ---
# Allows torch.load(weights_only=True) to deserialize Coqui config classes.
try:
    from torch.serialization import add_safe_globals

    allow = []

    # XTTS model/config
    try:
        from TTS.tts.configs.xtts_config import XttsConfig
        allow.append(XttsConfig)
    except Exception:
        pass
    try:
        from TTS.tts.models.xtts import XttsAudioConfig
        allow.append(XttsAudioConfig)
    except Exception:
        pass

    # Shared Coqui TTS configs commonly referenced by checkpoints
    try:
        from TTS.config.shared_configs import (
            BaseDatasetConfig,    # <— this is the one your last error asked for
            BaseAudioConfig,
            CharactersConfig,
        )
        allow += [BaseDatasetConfig, BaseAudioConfig, CharactersConfig]
    except Exception:
        pass
    try:
        from TTS.tts.configs.shared_configs import BaseTTSConfig
        allow.append(BaseTTSConfig)
    except Exception:
        pass

    if allow:
        add_safe_globals(allow)
except Exception as e:
    print(f"[XTTS] safe_globals setup skipped: {e}")


def init_xtts_model():
    global _xtts_model
    if _xtts_model is None:
        _xtts_model = load_xtts_model()

# === XTTS Voice Engine Access ===
def get_xtts_model():
    return _xtts_model

def set_current_speaker(name):
    global _current_speaker
    _current_speaker = name

def get_current_speaker():
    return _current_speaker

def set_use_xtts(state):
    global _use_xtts_clone
    _use_xtts_clone = state

def get_use_xtts():
    return _use_xtts_clone

def set_xtts_ref_wav(path):
    global _xtts_ref_wav
    _xtts_ref_wav = path

def get_xtts_ref_wav():
    return _xtts_ref_wav
