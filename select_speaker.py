import sounddevice as sd
import soundfile as sf
import numpy as np
from TTS.api import TTS
import tempfile
import os

# Initialize XTTS
tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False)
tts.to("cuda")

# List of speakers
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

def speak(text, speaker_name="Gracie Wise"):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tts.tts_to_file(
            text=text,
            speaker=speaker_name,
            language="en",
            file_path=f.name
        )
        audio, sr = sf.read(f.name, dtype='float32')
        sd.play(audio, sr)
        sd.wait()
        os.remove(f.name)

def choose_speaker():
    while True:
        for idx, speaker in enumerate(available_speakers):
            print(f"{idx}: {speaker}")
        try:
            index = int(input("Enter the number of the speaker to test: "))
            if 0 <= index < len(available_speakers):
                speaker = available_speakers[index]
                speak("This is how I sound. Do you want to keep me?", speaker)
                choice = input("Do you want to keep this voice? (y/n): ").strip().lower()
                if choice == 'y':
                    print(f"Selected voice: {speaker}")
                    break
            else:
                print("Invalid index. Try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

if __name__ == "__main__":
    choose_speaker()
