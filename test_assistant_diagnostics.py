# test_assistant_diagnostics.py

def test_gpu_cleanup():
    import torch, gc
    print("🧪 Testing GPU cleanup...")
    torch.cuda.empty_cache()
    gc.collect()
    print("✅ VRAM cleanup OK")

def test_xtts_init():
    from state import init_xtts_model, get_xtts_model
    print("🧪 Testing XTTS model init...")
    init_xtts_model()
    assert get_xtts_model() is not None
    print("✅ XTTS model loaded")

def test_speak():
    from tts_handler import speak_xtts
    from state import set_current_speaker, set_use_xtts, set_xtts_ref_wav
    print("🧪 Testing speech generation...")
    set_current_speaker("Abrahan Mack")
    set_use_xtts(False)
    speak_xtts("Hello, this is a test.")
    print("✅ Speech OK")

def test_transcribe():
    from transcriber import transcribe
    import os
    print("🧪 Testing transcriber...")
    if not os.path.exists("input.wav"):
        print("⚠️ No 'input.wav' found — skipping test.")
        return
    text = transcribe("input.wav")
    print(f"✅ Transcribed: {text}")

def test_llm():
    from llm_handler import generate_response
    print("🧪 Testing LLM...")
    result = generate_response("What's your name?")
    print(f"✅ LLM responded: {result}")

def test_voice_selector():
    from voice_selector import test_voice
    print("🧪 Testing voice selector current voice...")
    test_voice()
    print("✅ Voice test complete")

if __name__ == "__main__":
    print("\n=== IGOR Voice Assistant Diagnostics ===\n")
    test_gpu_cleanup()
    test_xtts_init()
    test_speak()
    test_transcribe()
    test_llm()
    test_voice_selector()
