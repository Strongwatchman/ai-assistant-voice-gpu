# AI Assistant Voice GPU

A real-time, locally-run conversational assistant powered by:
- 🧠 Whisper for speech recognition (CUDA-accelerated)
- 🗣️ XTTS for expressive multi-speaker voice synthesis
- 💬 llama.cpp for local LLM inference with GPU support
- 🎛️ Custom voice selector and voice cloning with Coqui TTS
- 🧩 Modular, script-driven architecture with stateful control

---

## 🚀 Features

- Fully GPU-accelerated on RTX 3050 or similar
- Hands-free voice input (Whisper.cpp)
- Fast, high-quality voice replies (XTTS v2 with speaker selection)
- Local LLM inference via llama.cpp (Zephyr/Mistral/7B models)
- Custom cloned voices (e.g. Optimus Prime, Mike Boudet)
- Multi-layer memory cleanup, logging, and GPU diagnostics
- Script-based modularity (Whisper, TTS, LLM, selector)

---

## 🛠️ Setup

See [venv_setup.md](venv_setup.md) for full install instructions.

Quick summary:

```bash
git clone https://github.com/Strongwatchman/ai-assistant-voice-gpu.git
cd ai-assistant-voice-gpu
python3 -m venv venv310
source venv310/bin/activate
pip install -r requirements.txt
- Copy webapp/.env.example to webapp/.env.local and set NEXT_PUBLIC_API_BASE
