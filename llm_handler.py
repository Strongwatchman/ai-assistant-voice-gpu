# llm_handler.py

import subprocess
import gc
import time
import logging
import os
import re
import traceback
from model_selector import get_selected_model

LLAMA_RUN_PATH = "/home/strongwatchman/AI_Assistant/llama.cpp/build/bin/llama-run"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(message)s')

def get_free_gpu_memory():
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,nounits,noheader"],
            encoding="utf-8"
        )
        free_memory = int(output.strip().split('\n')[0])
        return free_memory  # Already in MB
    except Exception as e:
        logger.warning(f"[VRAM] Could not read GPU memory via nvidia-smi: {e}")
        return 4096  # Fallback assumption

def gpu_available():
    try:
        subprocess.run(["nvidia-smi"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except:
        return False

def clean_gpu_memory():
    gc.collect()
    if gpu_available():
        try:
            subprocess.run(["nvidia-smi", "--gpu-reset"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass  # Ignore reset if unsupported
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
    output = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', output)
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
    import traceback
    from pathlib import Path

    try:
        model_path = get_selected_model()
        model_name = Path(model_path).name.lower()

        if not wait_for_memory():
            logger.warning("[VRAM] Proceeding despite low memory — will attempt anyway.")

        # Default LLM settings
        default_ngl = 24
        context_size = 2048
        formatted_prompt = prompt
        use_prompt_flag = True  # Default behavior: pass prompt as argument

        # Model-specific prompt formatting
        if "zephyr" in model_name or "mytho" in model_name or "mistral" in model_name:
            # OpenChat-style format (Zephyr, Mythomist, Mistral variants)
            formatted_prompt = f"<|user|>{prompt}<|assistant|>"
            use_prompt_flag = False  # These expect prompt from STDIN

        elif "airoboros" in model_name:
            # Airoboros chat format
            formatted_prompt = f"### Human:\n{prompt}\n### Assistant:"
            use_prompt_flag = True

        elif "openhermes" in model_name:
            formatted_prompt = f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant"
            use_prompt_flag = True

        elif "dan" in model_name or "adventurouswinds" in model_name:
            formatted_prompt = f"{prompt}"
            use_prompt_flag = False

        # Llama-run command
        cmd = [
            LLAMA_RUN_PATH,
            "--context-size", str(context_size),
            "--ngl", str(default_ngl),
            model_path
        ]

        if use_prompt_flag:
            cmd += ["--prompt", formatted_prompt]

        logger.info(f"[LLM] Launching: {' '.join(cmd)}")
        log_gpu_status("🔍 Before inference")

        start_time = time.time()
        if use_prompt_flag:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180)
        else:
            result = subprocess.run(cmd, input=formatted_prompt, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180)

        duration = time.time() - start_time
        output = result.stdout.strip()
        log_gpu_status("📊 After inference")

        logger.info(f"[LLM] Duration: {duration:.2f}s | Output length: {len(output)}")
        clean_gpu_memory()

        return clean_llama_output(output) or "🤖 No response generated."

    except subprocess.TimeoutExpired:
        return "⏱️ Timeout during response generation."

    except Exception as e:
        error_details = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        logger.error(f"❌ LLM Critical Failure:\n{error_details}")
        return f"❌ LLM error occurred:\n{error_details}"

