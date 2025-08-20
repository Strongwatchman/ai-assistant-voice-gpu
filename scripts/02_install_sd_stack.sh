#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/AI_Assistant"
SD_DIR="$ROOT/stable-diffusion-webui"
COMFY_DIR="$ROOT/ComfyUI"

echo ">>> Updating APT and installing small utilities (no driver changes)…"
sudo apt update
sudo apt install -y tmux htop # optional but useful

# ---------------- A1111 (its own venv, created by webui.sh) ----------------
if [ ! -d "$SD_DIR" ]; then
  echo ">>> Cloning Automatic1111…"
  git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git "$SD_DIR"
fi

# Configure A1111 to use GPU 0 (RTX 3050) + API + VRAM savers
cat > "$SD_DIR/webui-user.sh" <<'EOF'
#!/usr/bin/env bash
# Flags: xformers for speed, no-half-vae helps VRAM, split-attention lowers peak.
export COMMANDLINE_ARGS="--xformers --no-half-vae --opt-split-attention --api --listen --port 7860"
# Pin to GPU 0 (RTX 3050)
export CUDA_VISIBLE_DEVICES=0
EOF
chmod +x "$SD_DIR/webui-user.sh"

# First bootstrap (builds its venv). We don't fail the script if it exits non-zero first time.
echo ">>> Bootstrapping A1111 (first run compiles deps; may take a while)…"
pushd "$SD_DIR"
./webui.sh -f || true
popd

# ---------------- ComfyUI (separate venv) ----------------
if [ ! -d "$COMFY_DIR" ]; then
  echo ">>> Cloning ComfyUI…"
  git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFY_DIR"
fi

# Python venv for ComfyUI + Torch CUDA 12.1 wheels
echo ">>> Creating ComfyUI venv with CUDA 12.1 Torch…"
python3 -m venv "$COMFY_DIR/venv"
source "$COMFY_DIR/venv/bin/activate"
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r "$COMFY_DIR/requirements.txt"
deactivate

# GPU-specific runners for ComfyUI
cat > "$COMFY_DIR/run_2060.sh" <<'EOF'
#!/usr/bin/env bash
set -e
# Pin ComfyUI to GPU 1 (RTX 2060) and relax allocator for 6GB VRAM
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
source ./venv/bin/activate
python main.py --listen 0.0.0.0 --port 8189
EOF
chmod +x "$COMFY_DIR/run_2060.sh"

cat > "$COMFY_DIR/run_3050.sh" <<'EOF'
#!/usr/bin/env bash
set -e
export CUDA_VISIBLE_DEVICES=0
source ./venv/bin/activate
python main.py --listen 0.0.0.0 --port 8188
EOF
chmod +x "$COMFY_DIR/run_3050.sh"

# --------------- Convenience launcher for both UIs in tmux ----------------
cat > "$ROOT/run_sd_stack.sh" <<'EOF'
#!/usr/bin/env bash
set -e
# Start A1111 on GPU 0 (port 7860)
tmux new-session -d -s sd_a1111 "cd ~/AI_Assistant/stable-diffusion-webui && ./webui.sh -f"
sleep 6
# Start ComfyUI on GPU 1 (port 8189)
tmux new-session -d -s comfy_2060 "cd ~/AI_Assistant/ComfyUI && ./run_2060.sh"
echo ">>> A1111: http://localhost:7860"
echo ">>> ComfyUI (2060): http://localhost:8189"
echo ">>> Stop with: tmux kill-session -t sd_a1111 ; tmux kill-session -t comfy_2060"
EOF
chmod +x "$ROOT/run_sd_stack.sh"

echo ">>> Install complete."
echo "NEXT:"
echo "  1) Put a model file in: $SD_DIR/models/Stable-diffusion/   (e.g. SDXL base .safetensors)"
echo "  2) Launch both:  $ROOT/run_sd_stack.sh"
