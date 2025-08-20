#!/usr/bin/env python3
# ARC/ARK Voice Assistant – minimal console launcher (VRAM-friendly)

# --- path+boot preamble ---
import sys
from pathlib import Path as _P
_PR = _P(__file__).resolve().parents[1]
if str(_PR) not in sys.path:
    sys.path.insert(0, str(_PR))
try:
    from arc.boot import patch_torch_for_xtts
    patch_torch_for_xtts()  # allow XTTS to load with PyTorch >=2.6 safe_globals
except Exception as e:
    print(f"[XTTS] boot shim unavailable: {e}")
# --- end preamble ---

import arc.voice_handler as vh
import os, time, traceback, subprocess, shlex
from pathlib import Path

def print_banner():
    print("\n✅ Voice Assistant Ready.")
    print("🔘 Press Enter to speak | T = type | H = help")
    print("❌ Q to quit\n")

def _show_help():
    print("Commands:")
    print("  Enter  – record a short utterance (auto-stop on silence)")
    print("  T      – type your message instead of recording")
    print("  H      – show this help")
    print("  C      – choose voice")
    print("  V      – play a test line with current voice")
    print("  M      – choose LLM model")
    print("  S      – show current LLM model")
    print("  B      – quick model sanity check")
    print("  L      – test a question on ALL models, then pick one")
    print("  U      – mute/unmute assistant playback")
    print("  Q      – quit\n")

def _handle_user_input(ui: str):
    ui = ui.strip()

    # --- quits & help ---
    if ui.lower() == "q":
        print("👋 Exiting.")
        return False, None
    if ui.lower() == "h":
        _show_help()
        return True, None

    # --- typed mode ---
    if ui.lower() == "t":
        return True, input("📝 Type your message: ")

    # --- voice controls ---
    if ui.lower() == "c":
        from arc.voice_selector import choose_voice
        choose_voice()
        return True, None
    if ui.lower() == "v":
        from arc.voice_selector import test_voice
        test_voice()
        return True, None

    # --- LLM controls ---
    if ui.lower() == "m":
        from arc.model_selector import choose_model, get_selected_key, get_selected_model
        choose_model()
        try:
            k = get_selected_key() or "default"
            print(f"🧠 Using model: {k} ({Path(get_selected_model()).name})")
        except Exception as e:
            print(f"⚠️ Model selection applied, but failed to display: {e}")
        return True, None

    if ui.lower() == "s":
        from arc.model_selector import get_selected_key, get_selected_model
        try:
            k = get_selected_key() or "default"
            print(f"🧠 Model: {k} ({Path(get_selected_model()).name})")
        except Exception as e:
            print(f"⚠️ Unable to resolve model: {e}")
        return True, None

    if ui.lower() == "b":
        try:
            from arc.llm_handler import generate_response
            probe = "Say 'ready' in one word."
            print(f"🧪 Probing model with: {probe}")
            out = generate_response(probe)
            print(f"✅ Model replied: {out.strip()[:160]}")
        except Exception as e:
            print(f"❌ Sanity check failed: {e}")
        return True, None

    if ui.lower() == "l":
        # L = LLM roundup: run tester across ALL active models
        from arc.model_selector import list_active_keys, set_selected_key, get_selected_key
        tools_tester = Path.home() / "AI_Assistant" / "tools" / "test_llms_v3.py"
        if not tools_tester.exists():
            print(f"❌ Tester not found at {tools_tester}")
            return True, None

        q = input("📝 Enter the question to test on all models: ").strip()
        if not q:
            print("⚠️ No question provided.")
            return True, None

        cmd = [sys.executable, str(tools_tester), "-m", "all", "-q", q, "--show-cmd"]
        print(f"🔎 Running: {' '.join(shlex.quote(c) for c in cmd)}")

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        HARD_TIMEOUT = int(os.getenv("ARC_LLM_ROUNDUP_TIMEOUT", "600"))

        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, env=env
            )
            start = time.time()
            for line in iter(proc.stdout.readline, ''):
                print(line, end='', flush=True)
                if time.time() - start > HARD_TIMEOUT:
                    print("\n⏱️ Roundup exceeded timeout, terminating…")
                    proc.kill()
                    break
            rc = proc.wait(timeout=10)
            print(f"\n📦 Tester exited (rc={rc})")
        except Exception as e:
            print(f"❌ Failed to run tester: {e}")
            return True, None

        keys = list_active_keys()
        if not keys:
            print("⚠️ No active models discovered.")
            return True, None

        print("\n🧠 Models you can select now:")
        for i, k in enumerate(keys):
            print(f"  [{i}] {k}")

        raw = input("Pick a model # to use (Enter to keep current): ").strip()
        if raw == "":
            print(f"✅ Keeping: {get_selected_key() or 'default'}")
            return True, None

        try:
            idx = int(raw)
            if not (0 <= idx < len(keys)):
                raise ValueError
        except Exception:
            print("⚠️ Invalid selection. No change.")
            return True, None

        pick = keys[idx]
        set_selected_key(pick)
        print(f"✅ Selected model: {pick}")
        return True, None

    if ui.lower() == "u":
        try:
            if vh.is_speaking():
                vh.stop()
                print("🔇 Playback stopped.")
            else:
                print("ℹ️ Nothing is playing.")
        except Exception as e:
            print(f"⚠️ Couldn’t stop playback: {e}")
        return True, None

    # --- recording path (Enter) ---
    if ui == "":
        try:
            if vh.is_speaking():
                print("🔕 Stopping TTS for barge-in…")
                vh.stop()
        except Exception:
            pass

        from arc.audio import record_audio
        from arc.transcriber import transcribe
        record_audio("input.wav")
        try:
            text = transcribe("input.wav")
            print(f"🌐 Detected text: {text}")
            return True, text
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            return True, None

    # --- default: treat any other input as typed query ---
    return True, ui

def assistant_loop():
    from arc.llm_handler import generate_response
    while True:
        try:
            user_input = input("🟢 Your turn: ")
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Exiting.")
            break

        keep, query = _handle_user_input(user_input)
        if not keep:
            break
        if not query or not query.strip():
            print("⚠️ No input.")
            continue

        try:
            reply = generate_response(query)
            print(f"\n🤖 IGOR:\n{reply}\n")
            try:
                vh.speak(reply)
            except Exception as e:
                print(f"🗣️ (TTS skipped: {e})")
        except Exception:
            traceback.print_exc()
        time.sleep(0.05)

if __name__ == "__main__":
    print_banner()
    assistant_loop()

