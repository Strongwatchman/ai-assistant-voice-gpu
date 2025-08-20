#!/usr/bin/env bash
set -euo pipefail
COMFY_URL="${COMFY_URL:-http://127.0.0.1:8189}"
SESSION="${SESSION:-comfy_3050}"
PING="${PING:-/object_info/CheckpointLoaderSimple}"

echo "▶ Guard watching ${COMFY_URL}${PING} (tmux:${SESSION})"
while true; do
  if ! curl -s --max-time 5 "${COMFY_URL}${PING}" >/dev/null ; then
    echo "⚠️  ComfyUI unresponsive — restarting tmux session ${SESSION} ..."
    tmux kill-session -t "${SESSION}" 2>/dev/null || true
    ~/AI_Assistant/run_sd_stack.sh
    for i in {1..60}; do ss -lntp | grep -q ':8189' && break || sleep 1; done
    echo "✅ ComfyUI back."
  fi
  sleep 3
done
