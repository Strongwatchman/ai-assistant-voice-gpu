# Ensure Coqui TTS pickled classes can be loaded with PyTorch 2.6 (weights_only=True)
# This runs as soon as "arc.*" is imported (from arc.main import ... etc.)
try:
    from torch.serialization import add_safe_globals
    from contextlib import suppress

    allow = []

    # Coqui shared configs referenced by checkpoints
    with suppress(Exception):
        from TTS.config.shared_configs import (
            BaseDatasetConfig, BaseAudioConfig, CharactersConfig
        )
        allow += [BaseDatasetConfig, BaseAudioConfig, CharactersConfig]

    # XTTS model/config bits
    with suppress(Exception):
        from TTS.tts.configs.xtts_config import XttsConfig
        allow.append(XttsConfig)
    with suppress(Exception):
        from TTS.tts.models.xtts import XttsAudioConfig
        allow.append(XttsAudioConfig)
    with suppress(Exception):
        from TTS.tts.configs.shared_configs import BaseTTSConfig
        allow.append(BaseTTSConfig)

    if allow:
        add_safe_globals(allow)
        print("[XTTS] Added safe_globals:", ", ".join([c.__name__ for c in allow]))
except Exception as e:
    print(f"[XTTS] safe_globals setup skipped: {e}")

# --- Optional last-resort: revert Torch 2.6 default (only if still failing) ---
# import torch as _torch
# _old_load = _torch.load
# def _load(*a, **k):
#     k.setdefault("weights_only", False)  # pre-2.6 default
#     return _old_load(*a, **k)
# _torch.load = _load
# print("[XTTS] Patched torch.load(weights_only=False) as a fallback.")
