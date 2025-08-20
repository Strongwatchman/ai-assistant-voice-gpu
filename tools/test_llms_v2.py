#!/usr/bin/env python3
# tools/test_llms_v2.py — GGUF smoketest with per-model overrides (format/timeout/threads)

import argparse, os, sys, subprocess, textwrap
from pathlib import Path
from typing import List, Tuple

ROOT = Path.home() / "AI_Assistant"
LLAMA_BIN = ROOT / "llama.cpp" / "build" / "bin" / "llama-run"
MODELS_DIR = ROOT / "llama.cpp" / "models"

sys.path.insert(0, str(ROOT))
from arc.model_registry import MODEL_CONFIGS  # your registry (with paths & formats)

# ---- Per-model overrides (do NOT touch your registry while experimenting) ----
FORMAT_OVERRIDES = {
    # Suggested tweaks:
    "dolphin": "im_start",         # Dolphin often prefers ChatML
    "adventurous": "human_assistant",  # try a simple Human/Assistant scaffold
    # leave others alone unless you want to test alternatives
}

TIMEOUT_OVERRIDES = {
    # First load can be slow:
    "mythomist": 180,
}

# ---- Minimal prompt builder matching your formats ----
Chat = List[Tuple[str, str]]

def build_prompt(fmt: str, chat: Chat) -> str:
    fmt = (fmt or "raw").lower()
    if fmt == "openchat":
        parts=[]; sysmsg="\n".join(c for r,c in chat if r=="system")
        if sysmsg: parts.append(f"<|system|>\n{sysmsg}")
        for r,c in chat:
            if r=="user": parts.append(f"<|user|>\n{c}")
            elif r=="assistant": parts.append(f"<|assistant|>\n{c}")
        parts.append("<|assistant|>\n"); return "\n".join(parts)
    if fmt == "im_start":
        parts=[f"<|im_start|>{r}\n{c}<|im_end|>" for r,c in chat]
        parts.append("<|im_start|>assistant\n"); return "\n".join(parts)
    if fmt == "human_assistant":
        parts=[]; s="\n".join(c for r,c in chat if r=="system")
        if s: parts.append(f"System: {s}")
        for r,c in chat:
            if r=="user": parts.append(f"Human: {c}")
            elif r=="assistant": parts.append(f"Assistant: {c}")
        parts.append("Assistant: "); return "\n".join(parts)
    if fmt == "raw":
        s="\n".join(c for r,c in chat if r=="system")
        u="\n\n".join(c for r,c in chat if r=="user")
        return (s+"\n\n" if s else "") + u
    # fallback
    out=[f"{r.upper()}: {c}" for r,c in chat]; out.append("ASSISTANT:"); return "\n".join(out)

def main():
    ap = argparse.ArgumentParser(description="Quick GGUF smoketest via llama-run with per-model overrides.")
    ap.add_argument("-q","--query", default="In one sentence, tell me about permaculture gardening.")
    ap.add_argument("-m","--models", default="all", help="Comma-separated keys or 'all'")
    ap.add_argument("--ctx", type=int, default=None, help="Context size (overrides registry)")
    ap.add_argument("--ngl", type=int, default=None, help="GPU layers (overrides registry)")
    ap.add_argument("--temp", type=float, default=None, help="Temperature (overrides registry)")
    ap.add_argument("--threads", type=int, default=None, help="CPU threads for llama-run")
    ap.add_argument("--timeout", type=int, default=60, help="Default per-model timeout (seconds)")
    ap.add_argument("--show-cmd", action="store_true")
    args = ap.parse_args()

    if not LLAMA_BIN.exists():
        print(f"❌ llama-run not found at {LLAMA_BIN}"); sys.exit(2)

    keys = [k for k in MODEL_CONFIGS.keys() if k != "default"]
    if args.models.lower() != "all":
        req=[k.strip() for k in args.models.split(",") if k.strip()]
        bad=[k for k in req if k not in MODEL_CONFIGS]
        if bad: print(f"❌ Unknown keys: {bad}"); sys.exit(3)
        keys=req

    print(f"🧪 Testing {len(keys)} model(s): {', '.join(keys)}")
    print(f"📦 llama-run: {LLAMA_BIN}")
    print(f"📂 models dir: {MODELS_DIR}")

    # sensible threads default
    threads = args.threads if args.threads is not None else max(1, (os.cpu_count() or 4) // 2)

    for key in keys:
        cfg = MODEL_CONFIGS.get(key, MODEL_CONFIGS["default"])
        fmt = FORMAT_OVERRIDES.get(key, cfg.get("format","raw"))
        mpath = cfg.get("path")
        mfile = (MODELS_DIR / mpath) if mpath and not Path(mpath).is_absolute() else Path(mpath or "")

        print(f"\n— {key}:")
        if not mfile.exists():
            print(f"   ⚠️ Missing GGUF: {mfile}"); continue

        # Build prompt
        chat=[("system","You are IGOR, a concise and helpful voice assistant."), ("user", args.query)]
        prompt = build_prompt(fmt, chat)

        # Flags your llama-run supports
        ctx   = args.ctx  if args.ctx  is not None else int(cfg.get("context",2048))
        ngl   = args.ngl  if args.ngl  is not None else int(cfg.get("ngl",28))
        temp  = args.temp if args.temp is not None else float(cfg.get("temp",0.7))

        cmd=[str(LLAMA_BIN),
             "--context-size", str(ctx),
             "--ngl",          str(ngl),
             "--temp",         str(temp),
             "-t",             str(threads),
             str(mfile),       # positional: model
             prompt]           # positional: prompt

        if args.show_cmd:
            import shlex; print("   $", " ".join(shlex.quote(x) for x in cmd))

        timeout = TIMEOUT_OVERRIDES.get(key, args.timeout)
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            print(f"   ⏳ Timeout after {timeout}s"); continue

        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        preview = out[:800].replace("\n\n","\n")
        print("   ✅ Output:"); print(textwrap.indent(preview if preview else "(no output)","   "))
        if proc.returncode != 0: print(f"   ⚠️ llama-run exit code: {proc.returncode}")
        if err:
            tail="\n".join(err.splitlines()[-8:])
            if tail.strip():
                print("   🪵 stderr tail:"); print(textwrap.indent(tail,"   "))

if __name__ == "__main__":
    main()

