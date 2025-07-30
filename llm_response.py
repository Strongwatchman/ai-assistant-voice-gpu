# llm_response.py
from llama_cpp import Llama

# Path to the local GGUF model
MODEL_PATH = "/home/strongwatchman/AI_Assistant/llama.cpp/models/zephyr/zephyr-7b-alpha.Q4_K_M.gguf"

# Load the GGUF model
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=2048,
    n_threads=8,
    n_gpu_layers=35,
    use_mmap=True,
    use_mlock=False
)

import subprocess

def generate_response(prompt):
    result = subprocess.run(
        ["python", "llm_subprocess.py", prompt],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


