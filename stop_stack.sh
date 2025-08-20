#!/usr/bin/env bash
set -euo pipefail

# try to kill tmux sessions if used (best effort)
for S in comfy perch arc; do
  if tmux has-session -t "$S" 2>/dev/null; then
    echo "[stop_stack] killing tmux session: $S"
    tmux kill-session -t "$S" || true
  fi
done

# best-effort process kill (safe; ignores if not running)
pkill -f "python .*ComfyUI/main.py" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
pkill -f "node .*vite" 2>/dev/null || true
pkill -f "python .*arc/main.py" 2>/dev/null || true

echo "[stop_stack] done."
