# main.py

from transcriber import transcribe
from llm_handler import generate_response
from tts_handler import speak

def main():
    print("✅ Voice Assistant Ready. XTTS expressive model active.\n")
    print("🔘 Press Enter to talk | Type 'q' to quit")

    while True:
        user_input = input("🟢 Your turn: ").strip().lower()
        if user_input == 'q':
            print("👋 Exiting voice assistant.")
            break

        try:
            # Step 1: Record and transcribe user speech
            query = transcribe()
            print(f"📝 You said: {query}")

            if not query.strip():
                print("⚠️ No speech detected. Try again.")
                continue

            # Step 2: Generate LLM response
            reply = generate_response(query)
            print(f"🤖 Response: {reply}")

            # Step 3: Speak the response aloud
            speak(reply)

        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()

