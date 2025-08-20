#!/usr/bin/env python3
import argparse, os, sys, subprocess, textwrap
from pathlib import Path

ROOT = Path.home() / "AI_Assistant"
LLAMA_BIN = ROOT / "llama.cpp" / "build" / "bin" / "llama-run"
MODELS_DIR = ROOT / "llama.cpp" / "models"

sys.path.insert(0, str(ROOT))
from arc.model_registry import MODEL_CONFIGS

# minimal prompt builder for your formats
from typing import List, Tuple
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
    out=[f"{r.upper()}: {c}" for r,c in chat]; out.append("ASSISTANT:"); return "\n".join(out)

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Quick GGUF smoketest via llama-run using MODEL_CONFIGS.")
    ap.add_argument("-q","--query", default="In one sentence, tell me about permaculture gardening.")
    ap.add_argument("-m","--models", default="all")
    ap.add_argument("--ctx", type=int, default=None)
    ap.add_argument("--gpu-layers", type=int, default=None)
    ap.add_argument("--temp", type=float, default=None)
    ap.add_argument("--top-p", type=float, default=None)
    ap.add_argument("--n-predict", type=int, default=int(os.getenv("ARC_MAX_TOK","256")))  # kept for future, llama-run may ignore
    ap.add_argument("--seed", type=int, default=int(os.getenv("ARC_LLAMA_SEED","-1")))
    ap.add_argument("--timeout", type=int, default=60)
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

    for key in keys:
        cfg = MODEL_CONFIGS.get(key, MODEL_CONFIGS["default"])
        mpath = cfg.get("path")
        mfile = (MODELS_DIR / mpath) if mpath and not Path(mpath).is_absolute() else Path(mpath or "")
        print(f"\n— {key}:")
        if not mfile.exists():
            print(f"   ⚠️ Missing GGUF: {mfile}"); continue

        # Build prompt string
        chat=[("system","You are IGOR, a concise and helpful voice assistant."), ("user", args.query)]
        prompt = build_prompt(cfg.get("format","raw"), chat)

        # Build command: use only flags your llama-run supports
        ctx   = args.ctx if args.ctx is not None else int(cfg.get("context", 2048))
        ngl   = args.gpu_layers if args.gpu_layers is not None else int(cfg.get("ngl", 28))
        temp  = args.temp if args.temp is not None else float(cfg.get("temp", 0.7))

        # pick a reasonable default for CPU threads; tweak if needed
        threads = max(1, os.cpu_count() or 4)

        cmd = [
            str(LLAMA_BIN),
            "--context-size", str(ctx),
            "--ngl", str(ngl),
            "--temp", str(temp),
            "-t", str(threads),
            str(mfile),           # positional: model
            prompt,               # positional: prompt
        ]

        # If you ever want to use a Jinja chat template instead of inline tags:
        # cmd += ["--chat-template-file", str(MODELS_DIR / "templates" / "meta-llama-Llama-3.1-8B-Instruct.jinja"),
        #         "--jinja"]

        if args.show_cmd:
            import shlex; print("   $", " ".join(shlex.quote(x) for x in cmd))

        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=args.timeout)
        except subprocess.TimeoutExpired:
            print(f"   ⏳ Timeout after {args.timeout}s"); continue

        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        preview = out[:600].replace("\n\n","\n")
        print("   ✅ Output:"); print(textwrap.indent(preview if preview else "(no output)","   "))
        if proc.returncode != 0: print(f"   ⚠️ llama-run exit code: {proc.returncode}")
        if err:
            tail="\n".join(err.splitlines()[-8:]); print("   🪵 stderr tail:"); print(textwrap.indent(tail,"   "))

if __name__ == "__main__":
    main()

