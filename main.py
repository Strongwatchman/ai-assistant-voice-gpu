# Entry point: main.py
# This orchestrates the assistant loop with error handling, GPU cleanup, and modular triggers

import os
import time
import torch
import gc
from transcriber import transcribe
from llm_handler import generate_response
from tts_handler import speak_xtts
from recorder import record_audio
from keyboard_handler import listen_for_keypress  # placeholder
from state import init_xtts_model, get_xtts_model
from voice_selector import choose_voice, test_voice, toggle_xtts_clone

def clean_gpu_memory():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def initialize():
    print("🧹 Initializing assistant...")
    clean_gpu_memory()
    init_xtts_model()
    print("\n✅ Voice Assistant Ready. XTTS expressive model active.\n")
    print("🔘 Press Enter to talk | Type 't' to type | Press 'C' to choose voice")
    print("🎤 Press 'X' to toggle XTTS cloning | Press 'V' to test voice | Type 'q' to quit\n")

def handle_user_input(user_input):
    if user_input.lower() == 'q':
        print("👋 Exiting.")
        return False, None
    elif user_input.lower() == 't':
        query = input("📝 Type your message: ")
    elif user_input.lower() == 'c':
        choose_voice()
        return True, None
    elif user_input.lower() == 'v':
        test_voice()
        return True, None
    elif user_input.lower() == 'x':
        toggle_xtts_clone()
        return True, None
    elif user_input == '':
        record_audio("input.wav")
        try:
            query = transcribe("input.wav")
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            return True, None
        clean_gpu_memory()
    else:
        return True, None

    return True, query

def assistant_loop():
    initialize()
    while True:
        user_input = input("🟢 Your turn: ")
        continue_loop, query = handle_user_input(user_input)
        if not continue_loop:
            break
        if not query or not query.strip():
            print("⚠️  No input detected.")
            continue

        print(f"🗣️  You said: {query}")
        try:
            response = generate_response(query)
            print(f"🤖 IGOR: {response}")
        except Exception as e:
            print(f"❌ LLM error: {e}")
            continue
        finally:
            clean_gpu_memory()

        try:
            speak_xtts(response)
        except Exception as e:
            print(f"❌ TTS error: {e}")
        finally:
            clean_gpu_memory()

if __name__ == "__main__":
    try:
        assistant_loop()
    except Exception as e:
        import traceback
        print("\n❌ Critical error occurred:")
        traceback.print_exc()
        print("\n⚠️ Returned to shell safely.")

