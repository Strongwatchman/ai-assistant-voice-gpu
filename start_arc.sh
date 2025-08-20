#!/usr/bin/env bash
set -euo pipefail
ROOT="${ROOT:-$HOME/AI_Assistant}"
GPU="${ASSISTANT_CUDA:-0}"     # use RTX 3050 by default
VENV="${VENV:-$ROOT/venv310}"

source "$VENV/bin/activate"
export CUDA_VISIBLE_DEVICES="$GPU"
cd "$ROOT"
echo "[start_arc] Using CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES"
python -u arc/main.py
