# README Outline (Reference)

This is a lightweight outline to help continue development next session.

## Project: AI Assistant Voice GPU

### Sections to Maintain
1. **Overview**
   - Purpose: Local AI Assistant with GPU acceleration
   - Key components: ARC (assistant core), LLMs, TTS, STT, ComfyUI, SadTalker

2. **Repository Structure**
   - `arc/`: Core assistant modules
   - `tools/`: Utility scripts (audit, model tests, SD integration)
   - `scripts/`: Setup helpers
   - `ComfyUI/`, `comfy-perch/`: Image generation UI
   - `SadTalker/`: Animation attempts
   - `llama.cpp/`: Local LLM inference engine
   - `models/`: Model storage
   - `output/`, `tts_output/`, `logs/`: Generated results
   - `venv*/`: Virtual environments

3. **Features**
   - Voice assistant (Whisper + XTTS)
   - LLM selection and benchmarking
   - Image generation integration (ComfyUI)
   - Avatar experiments (SadTalker)
   - Repo audit and cleanup tools

4. **Getting Started**
   - Environment setup (Python 3.10, venv)
   - Model placement instructions
   - Launching with `start_arc.sh`

5. **Models**
   - LLMs in `llama.cpp/models/`
   - TTS voices and XTTS
   - Diffusion checkpoints in `ComfyUI/models/`

6. **Roadmap**
   - Avatar toggle in terminal + web UI
   - Web dashboard: LLM, voice, image, avatar, FoodscapeCoin integration
   - Expanded DAO and staking logic

7. **Contributing**
   - Fork & PR process
   - Issue tracking

8. **License**
   - Open-source license (MIT placeholder)

---

⚡ Next Session Goal: Use this outline as a jump start to refine docs and repo structure cleanup.
