✅ ARC + ARK project architecture

# 🎙️ ARC Voice Assistant + Foodscape Ecosystem (Offline-First, AI-Powered)

This repo powers the **Autonomous Resilience Core (ARC)** — a local-first, voice-enabled AI assistant designed to operate without cloud access or internet dependence. It uses open-source LLMs and TTS engines to create an intelligent, modular system for survival, learning, governance, and local organization.

It is the foundation of the **Foodscape Resilience Ecosystem**, a nonprofit initiative developed under **Foodscape Visions 501(c)(3)** to support regenerative agriculture, local economic sovereignty, and autonomous community governance through offline tools.

---

## 🧠 ARC + 📚 ARK System

- 🧠 **ARC** – *Autonomous Resilience Core*:  
  The AI controller that processes voice, text, and LLM interaction. Handles logic, task coordination, and staking logic — runs offline.

- 📚 **ARK** – *Autonomous Repository of Knowledge*:  
  A collection of modular, offline knowledge packs for permaculture, herbalism, composting, food preservation, DAO governance, and local resilience strategies.

Together, ARC + ARK form a fully local and resilient system for education, decision-making, and action — especially in low-trust or grid-down environments.

---

## ✅ Current Status: Functional Components

### 🎙️ AI Voice Assistant (ARC)
- ✔️ Text or voice input (mic supported via push-to-talk)
- ✔️ Local LLMs via `llama.cpp` (Zephyr, OpenHermes tested and stable)
- ✔️ Text-to-Speech output (Coqui TTS, XTTSv2)
- ✔️ Voice cloning from reference audio (WAV format)
- ✔️ Manual speaker selection
- ✔️ Command-line interface with keybinds
- ✔️ GPU acceleration on tested hardware (NVIDIA 3050, 8GB VRAM)
- ✔️ Fully offline-first — no cloud APIs or internet dependencies

### 🪙 Foodscape Coin (XRPL Testnet)
- ✔️ **FoodscapeCoin (FSC)** deployed on **XRPL Testnet**
- ✔️ Tested with **Xaman Wallet**
- ✔️ Trustline mechanics confirmed
- ❌ XRPL Mainnet token not yet deployed
- ❌ Staking Hooks and DAO reward logic under development

---

## 🚀 Quickstart

```bash
git clone https://github.com/Strongwatchman/ai-assistant-voice-gpu
cd ai-assistant-voice-gpu
pip install -r requirements.txt
python main.py

Follow prompts to select:
Your local LLM
Your voice model or clone
Mic input or manual CLI mode



---

🔮 ARC/ARK Roadmap
🧠 ARC Development

[x] Push-to-talk and mic input
[x] XTTS + Coqui TTS voice output
[x] Basic LLM routing (Zephyr, OpenHermes stable)

[ ] Refactor LLM engine for model switching and memory
[ ] Modular TTS handler with custom speaker selection
[ ] Config file for default voice/model
[ ] JSON-based lightweight memory
[ ] CLI flags for launching into specific ARK modules


📚 ARK Knowledge Packs

[ ] ark_apothecary.py – Herbalism + field medicine
[ ] ark_livestock.py – Animal care, rotation, feed
[ ] ark_preservation.py – Food drying, fermentation, canning
[ ] ark_irrigation.py – Gravity-fed, pump-free systems
[ ] ark_compost.py – Thermal piles, worms, EMO
[ ] ark_guilds.py – Companion planting, fruit tree guilds



---

🏛️ Foodscape DAO Token Vision

Built on the XRP Ledger, this future ecosystem will include:

Token	Purpose

🪙 FSC	Utility + staking token for governance access
🌱 FarmCoin	Used within local DAO projects for barter, goods, services
🏛️ DowCoin	Minted per project DAO for internal voting and decision-making


DAO Lifecycle

1. Proposal – A farm, apothecary, garden co-op submits DAO request


2. Review – Council or logic approves; FSC + DWC are issued


3. Staking Phase – Participants stake FSC for 3 years


4. Activation – Earn FarmCoin, use in local economy


5. Maturity – FSC unlocks, DAO can sponsor sub-DAOs



Staking and DAO logic will be enforced using XRPL Hooks. Development is active.


---

🛡️ Off-Grid Readiness

This system is being engineered to operate in grid-down or low-infra conditions:

🧱 Fully local — no internet access required

💾 USB-stick ready — portable resilience system

📃 Knowledge export to printable PDF homestead books

🖥️ Text fallback mode — runs without voice if needed

🔐 Encrypted local data storage planned



---

🛰️ Dual Mode Strategy: Online App + Offline Resilience

While our focus is offline-first infrastructure, we are also developing:

A mobile-friendly web app to interface with ARC + ARK systems

A cross-platform native mobile app (Android/iOS)

Secure local-first tools for DAO staking, voice control, and community governance

However, we fully anticipate a future where internet access may become unreliable or unavailable. ARC and ARK are designed to:

Run entirely without cloud APIs or external servers

Function on air-gapped systems or USB-stick installs

Operate in rural, remote, or post-collapse environments


> 🌐 When the grid is up, ARC will sync and update.
🛠️ When the grid is down, ARC will still serve.



Foodscape Visions is building for both the connected world and the collapsed one.


---

🤝 Get Involved

We are seeking:

🛠️ Developers:

Python (CLI routing, XRPL Hooks, offline UI)

Voice UX and audio performance

XRPL integration + staking logic

Mobile App User Interface 


📦 Contributors:

Writers and educators for ARK knowledge packs

Herbalists, permaculture designers, off-grid system testers

UI/UX or logo/brand designers


🎁 Supporters:

Donations to speed full-time development (pending 501(c)(3) approval)

Share this project with people who need resilience tools

Beta testers for early modules



---

🌿 About Foodscape Visions 501(c)(3)

Foodscape Visions is a nonprofit organization (EIN: ) focused on rebuilding local food economies through education, technology, and community action.

Our Mission:

> To cultivate thriving, sustainable communities by reconnecting people to food, land, and each other — through decentralized tools, regenerative agriculture, and localized economies.



ARC (Autonomous Resilience Core) and ARK (Autonomous Repository of Knowledge) are flagship tools being developed under Foodscape Visions to empower individuals and communities with offline-first access to AI, knowledge, and governance systems.

All ARC + ARK tools will remain open-source and aligned with our mission of bioregional sovereignty and food resilience.

Learn more at: https://foodscapevisions.org (coming soon)


---

📜 License

MIT — Use it, fork it, break it, fix it.
This is an open-source survival system in progress.


---

💼 Legal Status

Foodscape Visions is a nonprofit organization with IRS EIN # registered in Arizona.

✅ EIN issued

🕓 501(c)(3) status pending IRS approval (Form 1023 submitted)

❌ We do not yet claim tax-deductible donation status

✅ All project funds and development are managed under Foodscape Visions 501(c)(3)


This repository and all related tools are being developed under that public-benefit mission

