# arc/voice_selector.py — Lets user pick voice or clone, validate samples

import os
from arc.state import (
    set_current_speaker, set_xtts_ref_wav, set_use_xtts,
    get_xtts_model, get_current_speaker, get_use_xtts, get_xtts_ref_wav
)
from arc.tts_handler import speak_xtts_clone, speak_xtts_multispeaker

custom_voice_wavs = {
    'Mike Boudet (clone)': 'samples/mike_boudet.wav',
    'Optimus Prime (clone)': 'samples/optimus_prime.wav'
}

available_speakers = [
    'Claribel Dervla', 'Daisy Studious', 'Gracie Wise', 'Tammie Ema', 'Alison Dietlinde',
    'Ana Florence', 'Annmarie Nele', 'Asya Anara', 'Brenda Stern', 'Gitta Nikolina',
    'Henriette Usha', 'Sofia Hellen', 'Tammy Grit', 'Tanja Adelina', 'Vjollca Johnnie',
    'Andrew Chipper', 'Badr Odhiambo', 'Dionisio Schuyler', 'Royston Min', 'Viktor Eka',
    'Abrahan Mack', 'Adde Michal', 'Baldur Sanjin', 'Craig Gutsy', 'Damien Black',
    'Gilberto Mathias', 'Ilkin Urbano', 'Kazuhiko Atallah', 'Ludvig Milivoj', 'Suad Qasim',
    'Torcull Diarmuid', 'Viktor Menelaos', 'Zacharie Aimilios', 'Nova Hogarth', 'Maja Ruoho',
    'Uta Obando', 'Lidiya Szekeres', 'Chandra MacFarland', 'Szofi Granger', 'Camilla Holmström',
    'Lilya Stainthorpe', 'Zofija Kendrick', 'Narelle Moon', 'Barbora MacLean', 'Alexandra Hisakawa',
    'Alma María', 'Rosemary Okafor', 'Ige Behringer', 'Filip Traverse', 'Damjan Chapman',
    'Wulf Carlevaro', 'Aaron Dreschner', 'Kumar Dahl', 'Eugenio Mataracı', 'Ferran Simen',
    'Xavier Hayasaka', 'Luis Moray', 'Marcos Rudaski',
    'Mike Boudet (clone)', 'Optimus Prime (clone)'
]

def play_sample(text, speaker):
    model = get_xtts_model()
    if speaker in custom_voice_wavs:
        ref_path = custom_voice_wavs[speaker]
        if not os.path.exists(ref_path):
            print(f"❌ Missing reference sample: {ref_path}")
            return
        speak_xtts_clone(text, model, ref_path)
    else:
        speak_xtts_multispeaker(text, speaker, model)

def choose_voice():
    male_keywords = ["damien", "andrew", "craig", "gilberto", "aaron", "kumar", "mike", "optimus"]

    male_indices = [i for i, name in enumerate(available_speakers)
                    if name.lower().split()[0] in [k.split()[0] for k in male_keywords]
                    or any(m in name.lower() for m in male_keywords)]

    custom_indices = [i for i, name in enumerate(available_speakers) if name in custom_voice_wavs]
    female_indices = [i for i in range(len(available_speakers)) if i not in male_indices + custom_indices]

    print("\nMALE SPEAKERS:\n" + "\n".join(f"{i:2d}: {available_speakers[i]}" for i in male_indices))
    print("\nFEMALE SPEAKERS:\n" + "\n".join(f"{i:2d}: {available_speakers[i]}" for i in female_indices))
    print("\nCUSTOM CLONED SPEAKERS:\n" + "\n".join(f"{i:2d}: {available_speakers[i]}" for i in custom_indices))

    while True:
        choice = input("\nEnter speaker number or 'L' to loop all voices, 'Q' to quit: ").strip().lower()
        if choice == "l":
            for i, name in enumerate(available_speakers):
                print(f"\n[{i}] {name}")
                play_sample("This is how I sound. Do you want to keep me?", name)
        elif choice == "q":
            return
        elif choice.isdigit():
            idx = int(choice)
            if 0 <= idx < len(available_speakers):
                name = available_speakers[idx]
                play_sample("This is how I sound. Do you want to keep me?", name)
                confirm = input("Do you want to keep this voice? (y/n): ").strip().lower()
                if confirm == "y":
                    set_current_speaker(name)
                    set_xtts_ref_wav(custom_voice_wavs.get(name))
                    set_use_xtts(name in custom_voice_wavs)

                    # NEW: persist and make it effective for the next speak() call
                    _persist_voice(name)              # writes ~/.config/arc/voice.txt (via voice_paths)
                    os.environ["ARC_VOICE"] = name    # immediate, in-process override

                    print(f"✅ Voice set to: {name}")
                return

            else:
                print("❌ Invalid speaker number.")
        else:
            print("❌ Invalid input.")

def test_voice():
    model = get_xtts_model()
    speaker = get_current_speaker()
    use_clone = get_use_xtts()
    ref_wav = get_xtts_ref_wav()

    print("\n🔊 Testing current voice:")
    if use_clone:
        if not ref_wav or not os.path.exists(ref_wav):
            print(f"❌ Cloned reference sample missing: {ref_wav}")
            return
        speak_xtts_clone("This is how I sound using a cloned voice.", model, ref_wav)
    else:
        speak_xtts_multispeaker("This is how I sound using a multispeaker voice.", speaker, model)

def toggle_xtts_clone():
    current = get_use_xtts()
    new_state = not current
    set_use_xtts(new_state)
    print(f"🔁 Voice mode switched to: {'Voice Cloning' if new_state else 'Multispeaker'}")


# --- persistence helper injected ---
def _persist_voice(name: str):
    try:
        import os
        from .voice_paths import VOICE_FILE, ensure_dir
        ensure_dir()
        VOICE_FILE.write_text(name + '\n', encoding='utf-8')
        os.environ['ARC_VOICE'] = name
        print(f'💾 Saved default voice → {VOICE_FILE}')
    except Exception as e:
        print(f'⚠️ Could not persist voice: {e}')
