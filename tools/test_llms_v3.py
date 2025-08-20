#!/usr/bin/env python3
# tools/test_llms_v3.py — GGUF smoketest with per-model overrides + stop-tokens + refined prompts

import argparse, os, sys, subprocess, textwrap
from pathlib import Path
from typing import List, Tuple

ROOT = Path.home() / "AI_Assistant"
LLAMA_BIN  = ROOT / "llama.cpp" / "build" / "bin" / "llama-run"
MODELS_DIR = ROOT / "llama.cpp" / "models"

sys.path.insert(0, str(ROOT))
from arc.model_registry import MODEL_CONFIGS  # uses your paths & formats

MODEL_FILES = {
    # originals
    "zephyr":      "zephyr-7b-alpha.Q4_K_M.gguf",
    "openhermes":  "openhermes-2.5-mistral-7b.Q4_K_M.gguf",
    "dolphin":     "dolphin-2.6-mistral-7b.Q4_K_M.gguf",
    "mythomist":   "mythomist-7b.Q4_K_M.gguf",
    # "airoboros":   "airoboros-l2-7B-gpt4-m2.0.Q4_K_M.gguf",   # disabled
    # "adventurous": "dans-adventurouswinds-7b.Q4_K_M.gguf",   # disabled

    # new drops
    "aura":        "Aura-4B.i1-Q4_K_M.gguf",
    "daybreak":    "daybreak-kunoichi-2dpo-7b-q4_k_m.gguf",
    "daybreak_q8": "daybreak-kunoichi-2dpo-7b-q8_0.gguf",
    "dobby":       "dobby-8b-unhinged-q4_k_m.gguf",
    "stheno_q4":   "L3-8B-Stheno-v3.2-Q4_K_M-imat.gguf",
    "stheno_q8":   "L3-8B-Stheno-v3.2-Q8_0-imat.gguf",
    "magnum":      "magnum-v2-4b.i1-Q4_0.gguf",
    "spec3b":      "Spec-3b-q4_k_m.gguf",
    "specflash":   "Spec-flash-q4_k_m.gguf",
}


# ---- Per-model overrides while experimenting ----
FORMAT_OVERRIDES = {
    "dolphin":     "im_start",
    "mythomist":   "im_start",
    "airoboros":   "human_assistant",  # kept for reference
    "adventurous": "raw",
}

STOP_OVERRIDES = {
    "openhermes":  ["<|im_end|>"],
    "dolphin":     ["<|im_end|>"],
    "mythomist":   ["<|im_end|>"],
    "airoboros":   ["Human:"],
    # no stop tokens for adventurous
}

TEMP_OVERRIDES = {
    "adventurous": 0.50,
}

TIMEOUT_OVERRIDES = {
    "mythomist":  180,
    "airoboros":  180,
}

CTX_OVERRIDES = {
    "airoboros":  1024,
}
NGL_OVERRIDES = {
    "airoboros":  20,
}


# ---- Prompt builders (formats from your registry) ----
Chat = List[Tuple[str, str]]

def build_prompt(fmt: str, chat: Chat) -> str:
    fmt = (fmt or "raw").lower()

    if fmt == "openchat":
        parts = []
        sysmsg = "\n".join(c for r, c in chat if r == "system")
        if sysmsg:
            parts.append(f"<|system|>\n{sysmsg}")
        for r, c in chat:
            if r == "user":
                parts.append(f"<|user|>\n{c}")
            elif r == "assistant":
                parts.append(f"<|assistant|>\n{c}")
        parts.append("<|assistant|>\n")
        return "\n".join(parts)

    if fmt == "im_start":
        parts = [f"<|im_start|>{r}\n{c}<|im_end|>" for r, c in chat]
        parts.append("<|im_start|>assistant\n")
        return "\n".join(parts)

    if fmt == "human_assistant":
        parts = []
        for r, c in chat:
            if r == "user":
                parts.append(f"Human: {c}")
            elif r == "assistant":
                parts.append(f"Assistant: {c}")
        parts.append("Assistant: ")
        return "\n".join(parts)

    if fmt == "raw":
        user = "\n\n".join(c for r, c in chat if r == "user")
        return f"{user}\n\nAnswer in one short sentence.\nAssistant:"

    out = [f"{r.upper()}: {c}" for r, c in chat]
    out.append("ASSISTANT:")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Quick GGUF smoketest with per-model overrides and stop tokens.")
    ap.add_argument("-q","--query", default="In one sentence, tell me about the lost element of ether.")
    ap.add_argument("-m","--models", default="all", help="Comma-separated keys or 'all'")
    ap.add_argument("--ctx", type=int, default=None, help="Context size (overrides registry)")
    ap.add_argument("--ngl", type=int, default=None, help="GPU layers (overrides registry)")
    ap.add_argument("--temp", type=float, default=None, help="Temperature (overrides registry)")
    ap.add_argument("--threads", type=int, default=None, help="CPU threads")
    ap.add_argument("--timeout", type=int, default=60, help="Default per-model timeout (seconds)")
    ap.add_argument("--show-cmd", action="store_true")
    args = ap.parse_args()

    if not LLAMA_BIN.exists():
        print(f"❌ llama-run not found at {LLAMA_BIN}"); sys.exit(2)

    # build active model list
    keys = [k for k in MODEL_CONFIGS.keys() if k not in ("default", "airoboros", "adventurous")]
    if args.models.lower() != "all":
        req = [k.strip() for k in args.models.split(",") if k.strip()]
        bad = [k for k in req if k not in MODEL_CONFIGS]
        if bad:
            print(f"❌ Unknown keys: {bad}"); sys.exit(3)
        keys = req

    print(f"🧪 Testing {len(keys)} model(s): {', '.join(keys)}")
    print(f"📦 llama-run: {LLAMA_BIN}")
    print(f"📂 models dir: {MODELS_DIR}")

    threads = args.threads if args.threads is not None else max(1, (os.cpu_count() or 8) // 2)

    for key in keys:
        cfg = MODEL_CONFIGS.get(key, MODEL_CONFIGS["default"])
        fmt = FORMAT_OVERRIDES.get(key, cfg.get("format", "raw"))
        mpath = cfg.get("path")
        mfile = (MODELS_DIR / mpath) if mpath and not Path(mpath).is_absolute() else Path(mpath or "")

        print(f"\n— {key}:")
        if not mfile.exists():
            print(f"   ⚠️ Missing GGUF: {mfile}"); continue

        chat = [("system", "You are IGOR, a concise and helpful voice assistant."),
                ("user", args.query)]
        prompt = build_prompt(fmt, chat)

        ctx_default = int(cfg.get("context", 2048))
        ngl_default = int(cfg.get("ngl", 28))
        temp_default = float(cfg.get("temp", 0.7))

        ctx  = args.ctx  if args.ctx  is not None else int(CTX_OVERRIDES.get(key, ctx_default))
        ngl  = args.ngl  if args.ngl  is not None else int(NGL_OVERRIDES.get(key, ngl_default))
        temp = args.temp if args.temp is not None else float(TEMP_OVERRIDES.get(key, temp_default))

        timeout = TIMEOUT_OVERRIDES.get(key, args.timeout)

        cmd = [str(LLAMA_BIN),
               "--context-size", str(ctx),
               "--ngl",          str(ngl),
               "--temp",         str(temp),
               "-t",             str(threads),
               str(mfile),
               prompt]

        stops = STOP_OVERRIDES.get(key, [])
        for s in stops:
            cmd += ["--stop", s]

        if args.show_cmd:
            import shlex
            print("   $", " ".join(shlex.quote(x) for x in cmd))

        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            print(f"   ⏳ Timeout after {timeout}s"); continue

        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        preview = out[:800].replace("\n\n", "\n")
        print("   ✅ Output:"); print(textwrap.indent(preview if preview else "(no output)", "   "))
        if proc.returncode != 0: print(f"   ⚠️ llama-run exit code: {proc.returncode}")
        if err:
            tail = "\n".join(err.splitlines()[-8:])
            if tail.strip():
                print("   🪵 stderr tail:"); print(textwrap.indent(tail, "   "))


if __name__ == "__main__":
    main()

