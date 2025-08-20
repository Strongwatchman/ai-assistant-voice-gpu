# arc/xtts_loader.py — Loads XTTS voice synthesis model

from TTS.api import TTS
import torch

def load_xtts_model():
    """
    Load the XTTS voice synthesis model with GPU acceleration if available.
    Returns the loaded TTS model instance.
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
    print(f"🔊 Loading XTTS model on [{device}]...")
    tts = TTS(model_name)
    tts.to(device)
    return tts
