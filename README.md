# ARK (Autonomous Repository of Knowledge)

**ARK** is a locally-run, voice-enabled AI assistant built to support resilience, permaculture, off-grid living, and self-sovereignty in the face of modern digital chaos.

> Designed as both a daily-use assistant and a fallback digital sanctuary in case of systemic collapse.

## ⚙️ What It Does

- Runs multiple **GGUF LLMs** locally using GPU acceleration.
- Switchable **voice synthesis** (via Kōki TTS2 and custom cloned voices).
- Modular command-line interface for:
  - Choosing model
  - Activating voice
  - Listening and responding
- Intended future features:
  - Local/offline mobile app
  - Web UI (Famous.ai frontend)
  - Avatar-based personalities
  - Crypto DAO interaction (XRP Ledger: FoodScapeCoin, FarmCoin, DowCoin)
  - Knowledge modules for permaculture, herbal medicine, and biblical preparedness

## 🔧 How to Use

> ⚠️ Requirements: Python, GPU with 8GB+, Koqui TTS, GGUF-compatible runner

```bash
git clone https://github.com/Strongwatchman/ai-assistant-voice-gpu
cd ai-assistant-voice-gpu
# Setup your environment
pip install -r requirements.txt
# Run the main assistant
python main.py

Available Commands:
--load-model — Choose and load an LLM

--select-voice — Choose TTS voice or clone

--listen — Begin live voice input

--text — Use manual text input instead

🧠 Vision
ARK will eventually be available in three formats:

Local Terminal – Minimalist, apocalypse-ready CLI tool

Web UI/App – Visual interface with customizable characters

USB Edition – Fully offline, portable, text-only survival assistant

🛠️ Roadmap
 Multi-LLM support via GGUF

 Voice output (TTS2 + voice cloning)

 Command router module

 FastAPI wrapper for mobile integration

 Avatar/Character persona framework

 Crypto DAO governance module

🤝 Contributing
Want to help build the Ark? Create an Issue or Discussion below. We’re especially looking for help with:

Frontend/mobile UI

Voice input/UX design

Avatar animation (lightweight, offline-friendly)

Crypto logic (XRP Ledger)
