def patch_torch_for_xtts():
    """
    Make Coqui XTTS checkpoints load under PyTorch>=2.6 by allow-listing the
    classes used in the pickled config, and avoid cuDNN symbol issues.
    """
    import importlib
    import torch

    # 1) Add the config classes to PyTorch's safe unpickler
    added = []
    def _allow(mod, name):
        try:
            obj = getattr(importlib.import_module(mod), name)
            from torch.serialization import add_safe_globals
            add_safe_globals([obj])
            added.append(name)
        except Exception:
            pass

    # XTTS config bits that commonly appear in real checkpoints
    _allow("TTS.tts.configs.xtts_config", "XttsConfig")
    _allow("TTS.tts.models.xtts",          "XttsArgs")
    _allow("TTS.tts.models.xtts",          "XttsAudioConfig")
    _allow("TTS.config.shared_configs",    "BaseDatasetConfig")
    _allow("TTS.config.shared_configs",    "BaseTTSConfig")  # harmless if missing in your TTS version

    if added:
        print("[XTTS] Added safe_globals: " + ", ".join(added))
    else:
        print("[XTTS] Warning: no safe_globals added (imports may have changed).")

    # 2) Avoid cuDNN symbols that were crashing earlier
    try:
        torch.backends.cudnn.enabled = False
        print("[XTTS] cuDNN disabled for TTS to avoid symbol mismatch.")
    except Exception:
        pass
