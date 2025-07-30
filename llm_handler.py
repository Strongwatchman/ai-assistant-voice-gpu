import subprocess
import torch
import gc
import time
import logging
import os
import re

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

def wait_for_memory(threshold_mb=1500, max_attempts=10, delay=1.2):
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

def clean_llama_output(output: str) -> str:
    # Remove ANSI escape codes (like \x1b[K or \x1b[0m)
    output = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', output)

    # Filter out lines with LLM loading noise or assistant name
    lines = output.splitlines()
    filtered = [
        line for line in lines
        if not any(word in line.lower() for word in [
            "loading model", "ggml", "llama", "warning", "error",
            "initialize", "backend", "igor", "📊", "🧠", "🔍"
        ])
        and not line.strip().startswith("[")
        and line.strip()
    ]

    return "\n".join(filtered).strip()

def generate_response(prompt: str) -> str:
    if not wait_for_memory():
        logger.warning("[VRAM] Proceeding despite low memory — will attempt anyway.")

    formatted_prompt = f"<|system|>You are a helpful assistant.<|user|>{prompt}<|assistant|>"
    default_ngl = 24  # Max safe for RTX 3050 8GB with XTTS + Whisper
    context_size = 2048

    cmd = [
        LLAMA_RUN_PATH,
        "--context-size", str(context_size),
        "--ngl", str(default_ngl),
        MODEL_PATH,
        formatted_prompt
    ]

    logger.info(f"[LLM] Launching: {' '.join(cmd)}")
    try:
        log_gpu_status("🔍 Before inference")
        start_time = time.time()
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180)
        duration = time.time() - start_time
        output = result.stdout.strip()
        log_gpu_status("📊 After inference")
        logger.info(f"[LLM] Duration: {duration:.2f}s | Output length: {len(output)}")
        clean_gpu_memory()
        return clean_llama_output(output) or "🤖 No response generated."
    except subprocess.TimeoutExpired:
        return "⏱️ Timeout during response generation."
    except Exception as e:
        return f"❌ LLM failed: {e}"

