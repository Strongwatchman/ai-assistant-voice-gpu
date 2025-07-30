
import subprocess
import torch
import gc
import time
import logging
import os

MODEL_PATH = os.path.abspath("./models/zephyr-7b-alpha.Q4_K_M.gguf")
LLAMA_RUN_PATH = "/home/strongwatchman/AI_Assistant/llama.cpp/build/bin/llama-run"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(message)s')

def get_free_gpu_memory():
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
        free, _ = torch.cuda.mem_get_info()
        return free / (1024 * 1024)  # MB
    return 0

def clean_gpu_memory():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        gc.collect()

def log_gpu_status(header="GPU Status"):
    logger.info("=" * 80)
    logger.info(f"🧠 {header} — {time.strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        output = subprocess.run(["nvidia-smi"], stdout=subprocess.PIPE, text=True)
        logger.info(output.stdout)
    except Exception as e:
        logger.warning(f"[Diagnostics] Could not execute nvidia-smi: {e}")
    logger.info("=" * 80)

def wait_for_memory(threshold_mb=2100, max_attempts=12, delay=1.5):
    logger.info("[VRAM] Attempting memory release...")
    for attempt in range(1, max_attempts + 1):
        clean_gpu_memory()
        free_mem = get_free_gpu_memory()
        logger.info(f"[VRAM] Freeing memory attempt {attempt}... Free: {free_mem:.2f} MB")
        if free_mem >= threshold_mb:
            logger.info(f"[VRAM] Enough memory freed after {attempt} attempts.")
            return True
        time.sleep(delay)
    logger.warning(f"[VRAM] Cleanup failed: final free {get_free_gpu_memory():.2f} MB")
    return False

def generate_response(prompt: str) -> str:
    if not wait_for_memory():
        logger.warning("[VRAM] Proceeding despite insufficient memory.")

    ngl_attempts = [24, 16, 8, None]
    context_attempts = [4096, 2048, 1024]

    formatted_prompt = f"<|system|>You are a helpful assistant.<|user|>{prompt}<|assistant|>"

    for ngl in ngl_attempts:
        for ctx in context_attempts:
            free = get_free_gpu_memory()
            logger.info(f"[LLM] Trying with ngl={ngl}, context_size={ctx} | Free GPU: {free:.2f} MB")
            if ngl and free < 2100:
                logger.info(f"[LLM] Skipping ngl={ngl} due to insufficient VRAM")
                continue

            cmd = [LLAMA_RUN_PATH, "--context-size", str(ctx)]
            if ngl:
                cmd += ["--ngl", str(ngl)]
            cmd += [MODEL_PATH, formatted_prompt]

            logger.info(f"[LLM] Executing: {' '.join(cmd)}")

            try:
                log_gpu_status("🔍 Before subprocess")
                start_time = time.time()
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180)
                duration = time.time() - start_time
                output = result.stdout.strip()
                log_gpu_status("📊 After subprocess")
                logger.info(f"[LLM] Duration: {duration:.2f}s | Output length: {len(output)}")
                if output:
                    clean_gpu_memory()
                    return output
            except subprocess.TimeoutExpired:
                logger.warning(f"[LLM] Timeout (ngl={ngl}, ctx={ctx})")
            except Exception as e:
                logger.warning(f"[LLM] Error (ngl={ngl}, ctx={ctx}): {e}")

    logger.warning("[LLM] GPU attempts exhausted — switching to CPU")
    try:
        cpu_cmd = [LLAMA_RUN_PATH, "--context-size", "2048", MODEL_PATH, formatted_prompt]
        logger.info(f"[LLM] Executing CPU fallback: {' '.join(cpu_cmd)}")
        result = subprocess.run(cpu_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180)
        return result.stdout.strip() or "No response on CPU."
    except Exception as e:
        return f"❌ CPU LLM failure: {e}"
