# state.py

import torch
from TTS.api import TTS
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import XttsAudioConfig
from TTS.config.shared_configs import BaseDatasetConfig
from TTS.tts.models.xtts import XttsArgs

# Global state
_xtts_model = None
_use_xtts_clone = False
_current_speaker = "Damien Black"
_xtts_ref_wav = None

def init_xtts_model():
    global _xtts_model
    if _xtts_model is None:
        print("🚀 Loading XTTS model on GPU...")
        _xtts_model = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2").to("cuda")
        print("✅ XTTS model initialized on GPU.")

        
def get_xtts_model():
    return _xtts_model

def set_use_xtts(value: bool):
    global _use_xtts_clone
    _use_xtts_clone = value

def get_use_xtts():
    return _use_xtts_clone

def set_current_speaker(speaker: str):
    global _current_speaker
    _current_speaker = speaker

def get_current_speaker():
    return _current_speaker

def set_xtts_ref_wav(path: str):
    global _xtts_ref_wav
    _xtts_ref_wav = path

def get_xtts_ref_wav():
    return _xtts_ref_wav

