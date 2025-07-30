# AI Voice Assistant (Stable Local Build)

This is a **locally-run, voice-enabled AI assistant**, designed to operate without internet dependence using open-source models and tools.

Currently supports **text or voice interaction**, custom voice cloning, and modular LLMs via `gguf`.

## ✅ Current Features (Stable)

- 🧠 **Local LLMs (GGUF)**  
  - Supports multiple models (e.g., Nous, Mythomax, Mistral, etc.) * STILL JANKY OpenHermes works, Zephyr works, the others need tuning. 
  - Manual selection via CLI
- 🔊 **Voice Output**  
  - TTS via Kōki TTS2 (57+ voices)
  - Custom cloned voices (e.g., Optimus Prime, Mike Boudet)
- 🛠️ **Command-line interface**  
  - Simple terminal input to control LLM, voice, and input mode
- 📦 **Offline-first**  
  - Designed to run without cloud APIs
  - Works with local hardware: tested on NVIDIA 3050 (8GB), 32GB RAM, i7

## ⚠️ In Progress / Needs Work

- ❌ No session memory or chat threading yet
- ❌ LLM handler is *barely holding it together* — model routing is brittle
- ❌ No clean abstraction for voice/model handling
- ❌ No web/app integration yet

---

## 🚀 How to Run

```bash
git clone https://github.com/Strongwatchman/ai-assistant-voice-gpu
cd ai-assistant-voice-gpu
pip install -r requirements.txt

# Launch assistant
python main.py

# Follow the prompts to select:
# - Your LLM
# - Your voice (TTS or clone)
# - Text input or mic input

--------------------------

🔮 Future Direction (ARC/ARK System)
This project is planned to evolve into a larger modular system:
ARC (Autonomous Resilience Core) — the control center
ARK (Autonomous Repository of Knowledge) — specific knowledge modules (permaculture, medicine, crypto, etc.)
This voice assistant is the early alpha prototype that will power those future components.

## 🛣️ Roadmap
### 🔧 Core Assistant Features (Short-Term)
- [ ] Get better hardware for CUDA Development
- [ ] Refactor LLM handler to support dynamic switching, temp settings, max tokens
- [ ] Modular voice handler for quick swapping of TTS engines + clones
- [ ] Add persistent config file for user defaults (model, voice, input method)
- [ ] Build lightweight chat memory (context tracking, JSON-based)
- [ ] CLI flags for launching preferred ARK module quickly
- [ ] Build out USB-portable version (voice optional fallback)

### 🌱 Agricultural Knowledge Expansion
- [ ] Expand permaculture database (user-driven + curated)
- [ ] Add ARK modules for:
  - [ ] `ark_apothecary.py` – Herbal + real medicine
  - [ ] `ark_livestock.py` – Animals, husbandry, rotation systems
  - [ ] `ark_preservation.py` – Food storage, fermentation, solar drying

### 🪙 Crypto Infrastructure for Local Ag Commerce Projects
- [ ] Integrate XRP Ledger tooling via Python (XUMM API, XRPL-Py)
- [ ] Formalize `FoodScapeCoin` contract + testnet deployment
- [ ] Create staking rules (3-year hold for DAO participation)
- [ ] Issue `FarmCoin` for internal ag transactions (feed, seed, tools)
- [ ] Deploy `DowCoin` for DAO governance of individual projects
- [ ] Local-only wallet interface for trading + transparency (no exchanges)
- [ ] Trustless resource attribution (tractors, land, donations = token equity)

### 🏗️ Platform Development (Mid-Term)
- [ ] FastAPI server to expose assistant to mobile/web clients
- [ ] Modular UI to switch voices, ARKs, and sass levels (😐 → 😏 → 😈)
- [ ] User profiles with preferred characters, settings, and knowledge domains
- [ ] Model fallback detection + auto-reload (for weak GPUs)

### ⚔️ Off-Grid / Collapse Readiness
- [ ] Prepare “USB Stick of Wisdom” mode with minimal hardware requirements
- [ ] Create encrypted data archive (permaculture, first aid, recipes, crypto keys)
- [ ] AI fallback: text-only with no dependencies (ideal for refugees and bush dwellers)
- [ ] PDF print/export: Generate homestead survival books from ARK data

🤝 Want to Help?
Open an Issue or Discussion here on GitHub.

We’re looking for help with:

Python code cleanup
Model integration
Voice UX / personalities
Config + storage solutions

🧱 System Info
Tested on:

NVIDIA RTX 3050 (8GB)
Intel i7, 32GB RAM
Python 3.10
Ubuntu + Windows WSL2

📜 License
MIT — Use it, fork it, break it, fix it.
This is a survival tool in progress.

---------------------------------------

🏛️ DAO Governance Model: DowCoin + FoodScapeCoin
This system supports decentralized, region-based agricultural commerce using three tokens:
FoodScapeCoin (FSC) – Base utility + staking token
FarmCoin (FC) – Local commerce + goods exchange token
DowCoin (DWC) – Governance token for DAO project leadership

🪙 1. FoodScapeCoin (FSC)
Distributed to approved agricultural projects
Earn more FSC Coin by staking
Must be held/staked for 3 years
Generates passive yield over tim
Used as collateral for DAO governance participation
Can be used to purchase FarmCoin or vote in ecosystem-wide referenda

🐄 2. FarmCoin (FC)
Issued to users who stake FSC
Used for local barter and commerce (tools, seeds, feed, services)
Designed to be regional, not traded globally
Acts as a fluid economic token inside DAO projects

🎓 3. DowCoin (DWC)
Minted and distributed by each approved DAO project
Given to:
Project founders
Donors (based on resources contributed: land, equipment, labor)
Grants voting rights on:
Budget allocation
Project management decisions
Leadership changes
One DAO = One DAOCoin series (non-interchangeable)

🛠️ DAO Lifecycle
ProposalIndividual or org proposes an agricultural project: farm, garden co-op, apothecary, etc.
Review + OnboardingProject is reviewed by ARC DAO council (or automated logic).If accepted:
Initial FSC allocation is gifted
DWC is minted and distributed to stakeholders
Wallets + staking begin
Staking Period (3 Years)
Participants must stake FSC to remain in governance
Yield is accrued for holding
Early withdrawal burns yield
Commerce Activation
Participants earn FarmCoin through staking
FarmCoin is used to buy/sell/barter with local vendors or partner DAOs
Maturity + ExpansionAfter 3 years:
Staked FSC unlocks
DAO project may “franchise” or sponsor new DAOs
Voting thresholds may change

⚖️ Design Principles
Proof of Contribution: Real-world assets (land, tractors, labor) yield DWC
Staking = Skin in the Soil: Long-term commitment is rewarded
Local-first: Governance, economy, and commerce are designed for bioregional resilience
No Overlords: There is no central authority once DAOs are bootstrapped

🔐 Future Enhancements
Zero-knowledge proof voting for private ballots
AI assistant tools to help DAO founders create governance policies
Reputation scoring for DAO leaders (based on transparency + yields)
Dynamic yield schedules based on DAO performance metrics
