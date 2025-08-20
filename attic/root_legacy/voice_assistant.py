# === Enhanced Voice Assistant with XTTS Expressive Model and Emotional Tuning ===
import os
import sys
import shutil
import tempfile
import subprocess
import sounddevice as sd
import torchaudio
import torch
from TTS.api import TTS
from faster_whisper import WhisperModel
import re
import random

# === CONFIGURATION ===
TTS_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"
AUDIO_PATH = "/tmp/output.wav"
SLOWED_AUDIO_PATH = "/tmp/output_slow.wav"
LLAMA_RUN = "/home/strongwatchman/llama.cpp/build/bin/llama-run"
MODEL_PATH = "/home/strongwatchman/llama.cpp/models/zephyr/zephyr-7b-alpha.Q4_K_M.gguf"
SYSTEM_PROMPT = (
    "You are a warm and emotionally expressive assistant, like a beloved storyteller or teacher."
    " Your voice rises and falls with meaning, delivering both facts and wonder with heartfelt engagement."
    " Speak as someone who truly loves to teach, share, and care."
    " You are also an expert on technology and sustainable living topics, and you share your knowledge joyfully."
    " Use pauses, expressive emphasis, and emotion in your responses."
)
N_GPU_LAYERS = "28"
model_size = "tiny"

# === ENVIRONMENT CHECKS ===
def check_dependencies():
    missing = []
    if shutil.which("ffmpeg") is None: missing.append("ffmpeg")
    if shutil.which("ffplay") is None: missing.append("ffplay")
    if not os.path.isfile(LLAMA_RUN): missing.append("llama-run binary")
    if not os.path.isfile(MODEL_PATH): missing.append("model file")
    if missing:
        print("\n🚫 Missing dependencies:", ", ".join(missing))
        sys.exit(1)

# === TTS SETUP ===
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
tts = TTS(model_name=TTS_MODEL, progress_bar=False)
tts.to("cuda")
tts_config = tts.config
available_speakers = [
    'Claribel Dervla', 'Daisy Studious', 'Gracie Wise', 'Tammie Ema', 'Alison Dietlinde', 'Ana Florence',
    'Annmarie Nele', 'Asya Anara', 'Brenda Stern', 'Gitta Nikolina', 'Henriette Usha', 'Sofia Hellen',
    'Tammy Grit', 'Tanja Adelina', 'Vjollca Johnnie', 'Andrew Chipper', 'Badr Odhiambo', 'Dionisio Schuyler',
    'Royston Min', 'Viktor Eka', 'Abrahan Mack', 'Adde Michal', 'Baldur Sanjin', 'Craig Gutsy',
    'Damien Black', 'Gilberto Mathias', 'Ilkin Urbano', 'Kazuhiko Atallah', 'Ludvig Milivoj', 'Suad Qasim',
    'Torcull Diarmuid', 'Viktor Menelaos', 'Zacharie Aimilios', 'Nova Hogarth', 'Maja Ruoho', 'Uta Obando',
    'Lidiya Szekeres', 'Chandra MacFarland', 'Szofi Granger', 'Camilla Holmström', 'Lilya Stainthorpe',
    'Zofija Kendrick', 'Narelle Moon', 'Barbora MacLean', 'Alexandra Hisakawa', 'Alma María',
    'Rosemary Okafor', 'Ige Behringer', 'Filip Traverse', 'Damjan Chapman', 'Wulf Carlevaro',
    'Aaron Dreschner', 'Kumar Dahl', 'Eugenio Mataracı', 'Ferran Simen', 'Xavier Hayasaka',
    'Luis Moray', 'Marcos Rudaski'
]

# === TTS Playback ===
def speak(text):
    try:
        text = re.sub(r'([.!?])', r'\1 <break time=300ms/>', text)
        text = re.sub(r'([,;])', r'\1 <break time=150ms/>', text)
        speaker = random.choice(available_speakers)
        tts.tts_to_file(
            text=text.strip(),
            file_path=AUDIO_PATH,
            speaker=speaker,
            language="en",
            split_sentences=True
        )
        subprocess.run(["ffmpeg", "-y", "-i", AUDIO_PATH, "-filter:a", "atempo=0.95", SLOWED_AUDIO_PATH], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["ffplay", "-nodisp", "-autoexit", SLOWED_AUDIO_PATH], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"TTS error: {e}")

# === WHISPER ===
whisper_model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")

# === MAIN LOGIC ===
def main():
    check_dependencies()
    print("✅ Voice Assistant Ready. XTTS expressive model active.")

    while True:
        try:
            key = input("\n🔘 Enter = talk | Q = quit: ").strip().lower()
            if key == "q": break

            print("🎙️ Speak now... (auto-stop on silence)")
            recording = sd.rec(int(10 * 16000), samplerate=16000, channels=1)
            sd.wait()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
                torchaudio.save(temp_audio.name, torch.tensor(recording).T, 16000)
                segments, _ = whisper_model.transcribe(temp_audio.name)
            user_text = " ".join([seg.text for seg in segments])
            print(f"📝 You said: {user_text}")

            prompt = SYSTEM_PROMPT + f"\n\nUser: {user_text}\nAssistant:"
            llama_proc = subprocess.run(
                [LLAMA_RUN,
                 "--model", MODEL_PATH,
                 "--n-predict", "300",
                 "--temp", "0.7",
                 "--repeat_penalty", "1.1",
                 "--top_k", "100",
                 "--top_p", "0.95",
                 "--ngl", N_GPU_LAYERS,
                 prompt],
                text=True,
                capture_output=True
            )

            raw_output = llama_proc.stdout.strip()
            if llama_proc.returncode != 0 or not raw_output:
                print("❌ LLM error.")
                print(f"🔍 STDERR: {llama_proc.stderr.strip()}")
                speak("Sorry, the assistant encountered an error. Check logs for details.")
                continue

            response = re.sub(r'\x1b\[[0-9;]*m', '', raw_output)
            if "Assistant:" in response:
                response = response.split("Assistant:")[-1].strip()
            response = " ".join([re.sub(r'\(.*?\)', '', l).strip() for l in response.splitlines() if l.strip()])

            print(f"🗣️ Assistant says: {response}")
            speak(response)
        except KeyboardInterrupt:
            print("\n👋 Exiting...")
            break
        except Exception as ex:
            print(f"⚠️ Error: {ex}")
            continue

if __name__ == "__main__":
    main()

