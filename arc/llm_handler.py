# arc/llm_handler.py
import os, subprocess, time, logging, re, traceback, shlex
from pathlib import Path

from arc.model_selector import get_selected_model, get_selected_key
from arc.model_registry import MODEL_CONFIGS
from arc.prompt_formatting import format_prompt, get_effective_format, get_stop_tokens

LLAMA_RUN_PATH = "/home/strongwatchman/AI_Assistant/llama.cpp/build/bin/llama-run"

# Env-tunable runtime knobs
DEFAULT_TIMEOUT = int(os.getenv("ARC_LLM_TIMEOUT", "180"))
DEFAULT_THREADS = int(os.getenv("ARC_LLM_THREADS", max(1, (os.cpu_count() or 8)//2)))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")

_ANSI = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

def _ansi_strip(s: str) -> str:
    return _ANSI.sub("", s)

def _clean(text: str) -> str:
    junk_prefixes = ("loading", "ggml", "llama", "warning", "error", "igor", "[", "📊", "🧠", "🔍")
    lines = []
    for ln in _ansi_strip(text).splitlines():
        t = ln.strip()
        if not t:
            continue
        if any(t.lower().startswith(j) for j in junk_prefixes):
            continue
        lines.append(t)
    return "\n".join(lines).strip()

def _active_cfg():
    key = get_selected_key() or "default"
    cfg = MODEL_CONFIGS.get(key, MODEL_CONFIGS["default"])
    gguf = Path(get_selected_model())
    if not gguf.exists():
        raise FileNotFoundError(f"Model file not found: {gguf}")
    return key, cfg, gguf

def generate_response(user_text: str) -> str:
    try:
        key, cfg, gguf = _active_cfg()

        # Build prompt identical to tester
        fmt = get_effective_format(key, cfg.get("format"))
        system_text = "You are IGOR, a concise and helpful voice assistant."
        prompt = format_prompt(user_text, fmt, system_text=system_text)

        # Runtime knobs (env overrides > registry)
        ctx   = int(os.getenv("ARC_LLM_CTX",    cfg.get("context", 2048)))
        ngl   = int(os.getenv("ARC_LLM_NGL",    cfg.get("ngl", 24)))
        temp  = float(os.getenv("ARC_LLM_TEMP", cfg.get("temp", 0.7)))
        threads = DEFAULT_THREADS
        timeout = DEFAULT_TIMEOUT
        if "ARC_LLM_THREADS" in os.environ: threads = int(os.environ["ARC_LLM_THREADS"])
        if "ARC_LLM_TIMEOUT" in os.environ: timeout = int(os.environ["ARC_LLM_TIMEOUT"])

        cmd = [
            LLAMA_RUN_PATH,
            "--context-size", str(ctx),
            "--ngl", str(ngl),
            "--temp", str(temp),
            "-t", str(threads),
        ]

        # Per-model stop tokens (same as tester)
        stops = get_stop_tokens(key)
        for s in stops:
            cmd += ["--stop", s]

        # IMPORTANT: many builds don't support --top-p; only add if explicitly requested
        if "ARC_LLM_TOP_P" in os.environ:
            cmd += ["--top-p", str(float(os.environ["ARC_LLM_TOP_P"]))]

        # Positional model + prompt (this matched the tester)
        cmd += [str(gguf), prompt]

        logger.info(f"[LLM] Model: {key} ({gguf.name}) fmt={fmt} ctx={ctx} ngl={ngl} temp={temp}")
        if stops:
            logger.info(f"[LLM] Stops: {stops}")
        logger.info(f"[LLM] Cmd: {' '.join(shlex.quote(c) for c in cmd)}")

        t0 = time.time()
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
        dur = time.time() - t0
        out = proc.stdout or ""
        text = _clean(out) or "🤖 (no text)"
        logger.info(f"[LLM] Done in {dur:.2f}s (rc={proc.returncode})")

        if proc.returncode != 0:
            # show last lines of raw output to aid debugging
            tail = "\n".join((out.splitlines() or [])[-24:])
            logger.info("[LLM] Raw tail:\n" + tail)
        return text

    except subprocess.TimeoutExpired:
        return "⏱️ Timeout during response generation."
    except Exception:
        return f"❌ LLM error:\n{traceback.format_exc()}"

