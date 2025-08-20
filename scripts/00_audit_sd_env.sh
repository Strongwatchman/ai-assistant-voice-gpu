#!/usr/bin/env bash
set -euo pipefail

ROOT="${HOME}/AI_Assistant"
REPORT="${ROOT}/audit_report_$(date +%F_%H-%M-%S).md"
mkdir -p "${ROOT}/scripts"

section () { echo -e "\n## $1\n" >>"$REPORT"; }
kv () { printf -- "- **%s**: %s\n" "$1" "$2" >>"$REPORT"; }
code () { echo -e "\n\`\`\`\n$1\n\`\`\`\n" >>"$REPORT"; }
run () { echo -e "\n\`\`\`\n$($@ 2>&1 || true)\n\`\`\`\n" >>"$REPORT"; }

echo "# AI/SD Environment Audit ($(date))" >"$REPORT"
kv "Host" "$(hostname)"
kv "User" "$USER"
kv "Root folder" "$ROOT"

# ---------- GPUs / Drivers ----------
section "GPU / Driver / CUDA"
if command -v nvidia-smi >/dev/null 2>&1; then
  run nvidia-smi
else
  echo "- **nvidia-smi**: NOT FOUND" >>"$REPORT"
fi
for so in /usr/lib/x86_64-linux-gnu/libcuda.so* /usr/local/cuda/version.txt; do
  [ -e "$so" ] && kv "Found" "$so"
done

# ---------- System packages ----------
section "System Packages"
run ffmpeg -version
run git --version
run tmux -V
run htop --version

# ---------- Python / pyenv ----------
section "Python / pyenv"
run python3 --version
if command -v pyenv >/dev/null 2>&1; then
  run pyenv versions
  run pyenv which python
else
  echo "- **pyenv**: NOT FOUND" >>"$REPORT"
fi

# ---------- Folder layout ----------
section "Folder Layout"
if [ -d "$ROOT" ]; then
  run bash -lc "ls -lah ${ROOT}"
  [ -d "${ROOT}/arc" ] && run bash -lc "ls -lah ${ROOT}/arc"
else
  echo "- **AI_Assistant folder** not found at ${ROOT}" >>"$REPORT"
fi

# ---------- A1111 ----------
section "Automatic1111 (stable-diffusion-webui)"
SD="${ROOT}/stable-diffusion-webui"
if [ -d "$SD" ]; then
  kv "Path" "$SD"
  [ -f "${SD}/webui-user.sh" ] && { kv "webui-user.sh" "FOUND"; code "$(grep -E 'COMMANDLINE_ARGS|CUDA_VISIBLE_DEVICES' -n ${SD}/webui-user.sh || true)"; }
  [ -d "${SD}/venv" ] && { kv "venv" "FOUND"; run bash -lc "source ${SD}/venv/bin/activate && python -V && pip show torch torchvision xformers | sed 's/^/  /'"; }
  [ -d "${SD}/models/Stable-diffusion" ] && run bash -lc "ls -lah ${SD}/models/Stable-diffusion"
  [ -d "${SD}/extensions" ] && run bash -lc "ls -lah ${SD}/extensions | grep -E 'controlnet|deforum|animatediff|adetailer|roop' || true"
else
  echo "- **A1111**: NOT PRESENT" >>"$REPORT"
fi

# ---------- ComfyUI ----------
section "ComfyUI"
COMFY="${ROOT}/ComfyUI"
if [ -d "$COMFY" ]; then
  kv "Path" "$COMFY"
  [ -d "${COMFY}/venv" ] && { kv "venv" "FOUND"; run bash -lc "source ${COMFY}/venv/bin/activate && python -V && pip show torch torchvision | sed 's/^/  /'"; }
  [ -f "${COMFY}/run_2060.sh" ] && { kv "run_2060.sh" "FOUND"; code "$(sed -n '1,120p' ${COMFY}/run_2060.sh)"; }
  [ -f "${COMFY}/run_3050.sh" ] && { kv "run_3050.sh" "FOUND"; code "$(sed -n '1,120p' ${COMFY}/run_3050.sh)"; }
else
  echo "- **ComfyUI**: NOT PRESENT" >>"$REPORT"
fi

# ---------- Services / Ports ----------
section "Services / Ports"
run bash -lc "systemctl --type=service --state=running | grep -Ei 'a1111|comfy|stable|diffusion' || true"
run bash -lc "ss -lntp | grep -E ':7860|:8188|:8189' || true"
# Try API probes (won't fail script if down)
section "API Probes"
run bash -lc "curl -s http://127.0.0.1:7860/sdapi/v1/sd-models | head -n 5"
run bash -lc "curl -s http://127.0.0.1:8188 | head -n 5"
run bash -lc "curl -s http://127.0.0.1:8189 | head -n 5"

# ---------- arc code ----------
section "ARC Code Snapshot"
if [ -d "${ROOT}/arc" ]; then
  run bash -lc "find ${ROOT}/arc -maxdepth 2 -type f -name '*.py' -printf '%p\n' | sort"
  # show main files if exist
  for f in "${ROOT}/arc/main.py" "${ROOT}/arc/sd_client.py" "${ROOT}/arc/comfy_client.py"; do
    [ -f "$f" ] && { echo -e "\n### $(basename "$f")\n" >>"$REPORT"; code "$(sed -n '1,200p' "$f")"; }
  done
fi

echo -e "\n---\n**Report saved:** ${REPORT}"
echo "${REPORT}"
