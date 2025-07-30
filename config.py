# config.py

import os

# XTTS configuration
TTS_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"
AUDIO_PATH = "/tmp/output.wav"
SLOWED_AUDIO_PATH = "/tmp/output_slow.wav"

# LLM model configuration
LLAMA_RUN = "/home/strongwatchman/llama.cpp/build/bin/llama-run"
MODEL_PATH = "/home/strongwatchman/llama.cpp/models/zephyr/zephyr-7b-alpha.Q4_K_M.gguf"
N_GPU_LAYERS = "28"

# Prompt
SYSTEM_PROMPT = (
    "You are a warm and emotionally expressive assistant, like a beloved storyteller or teacher."
    " Your voice rises and falls with meaning, delivering both facts and wonder with heartfelt engagement."
    " Speak as someone who truly loves to teach, share, and care."
    " You are also an expert on technology and sustainable living topics, and you share your knowledge joyfully."
    " Use pauses, expressive emphasis, and emotion in your responses."
)

# Whisper
WHISPER_MODEL_SIZE = "tiny"

# Environment
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

