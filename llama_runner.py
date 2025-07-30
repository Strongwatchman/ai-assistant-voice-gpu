# llama_runner.py

import subprocess
import shutil
import os
import torch

MODEL_PATH = "/home/strongwatchman/llama.cpp/models/zephyr/zephyr-7b-alpha.Q4_K_M.gguf"
LLAMA_CPP_PATH = "/home/strongwatchman/llama.cpp"
DEFAULT_TEMP_FILE = "llm_reply.txt"

def run_llm_query(prompt, temp_file=DEFAULT_TEMP_FILE):
    # Check for GPU availability
    has_gpu = torch.cuda.is_available()
    fallback_ngl = [24, 20, 16, 12, 8, 4]

    if has_gpu:
        mem_free = torch.cuda.mem_get_info()[0] / 1024**2
        print(f"[LLM] GPU available. Free memory: {mem_free:.2f} MB")
    else:
        print("[LLM] No CUDA GPU detected. Using CPU.")
        fallback_ngl = []

    for ngl in fallback_ngl:
        print(f"[LLM] Attempting with --ngl {ngl}, free GPU memory: {mem_free:.2f} MB")
        result = _run_llama(prompt, ngl=ngl, temp_file=temp_file)
        if result:
            return result

    # CPU fallback
    print("[LLM] GPU attempts exhausted — switching to CPU.")
    return _run_llama(prompt, ngl=None, temp_file=temp_file)

def _run_llama(prompt, ngl=None, temp_file=DEFAULT_TEMP_FILE):
    llama_bin = shutil.which("llama-run") or os.path.join(LLAMA_CPP_PATH, "llama-run")
    if not os.path.exists(llama_bin):
        print("❌ llama-run not found!")
        return None

    command = [
        llama_bin,
        "-m", MODEL_PATH,
        "-p", prompt,
        "--n-predict", "250",
        "--temp", "0.8"
    ]

    if ngl:
        command += ["--ngl", str(ngl)]

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        output = result.stdout.strip()

        # Filter garbage responses
        if not output or "error" in output.lower():
            return None

        # Save to file if needed
        with open(temp_file, "w") as f:
            f.write(output)

        return output

    except subprocess.TimeoutExpired:
        print("⚠️ LLM call timed out.")
        return None
    except Exception as e:
        print(f"⚠️ LLM error: {e}")
        return None
