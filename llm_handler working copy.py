# llm_handler.py

import subprocess
import time
from pynvml import nvmlInit, nvmlDeviceGetHandleByIndex, nvmlDeviceGetMemoryInfo

nvmlInit()

def get_free_gpu_mem_mb(idx=0):
    handle = nvmlDeviceGetHandleByIndex(idx)
    info = nvmlDeviceGetMemoryInfo(handle)
    return info.free / (1024 * 1024)

def generate_response(prompt: str) -> str:
    ngl = 24  # Start high and decrement
    model_path = "./llama.cpp/models/zephyr/zephyr-7b-alpha.Q4_K_M.gguf"
    llama_bin = "./llama.cpp/build/bin/llama-run"

    while True:
        print(f"[LLM] Attempting with --ngl {ngl}, free GPU memory: {get_free_gpu_mem_mb():.2f} MB")
        cmd = [
            llama_bin,
            model_path,
            "--ngl", str(ngl),
            "--n-predict", "100",
            "--temp", "0.7",
            prompt
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            output = result.stdout.strip()
            if output:
                return output
        except Exception as e:
            return f"LLM error: {e}"

        if ngl > 4:
            ngl -= 4
            print(f"[LLM] No output — lowering ngl to {ngl} and retrying...")
            time.sleep(2)
        else:
            print("[LLM] GPU attempts exhausted — switching to CPU.")
            cmd[cmd.index("--ngl") + 1] = "0"
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                return result.stdout.strip() or "No response on CPU either."
            except Exception as e:
                return f"CPU LLM error: {e}"
