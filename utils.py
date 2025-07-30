# utils.py

import shutil
import os
from config import LLAMA_RUN, MODEL_PATH

def check_dependencies():
    missing = []
    if shutil.which("ffmpeg") is None: missing.append("ffmpeg")
    if shutil.which("ffplay") is None: missing.append("ffplay")
    if not os.path.isfile(LLAMA_RUN): missing.append("llama-run binary")
    if not os.path.isfile(MODEL_PATH): missing.append("model file")
    if missing:
        print("\n🚫 Missing dependencies:", ", ".join(missing))
        exit(1)

