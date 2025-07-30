# model_selector.py
import os
from pathlib import Path

MODEL_DIR = Path("./models")
SELECTION_FILE = Path(".selected_model")


def list_models():
    gguf_files = sorted([f for f in MODEL_DIR.glob("*.gguf")])
    return gguf_files


def print_model_menu(models, default_name):
    print("\n🧠 Available GGUF Models:\n")
    for idx, model in enumerate(models, 1):
        label = " (default)" if default_name in str(model.name) else ""
        print(f"{idx}. {model.name}{label}")
    print("\nEnter model number to select it, or press Enter to keep current selection.")


def choose_model():
    models = list_models()
    if not models:
        print("❌ No .gguf models found in ./models directory.")
        return None

    default_model = "zephyr-7b-alpha.Q4_K_M.gguf"
    print_model_menu(models, default_model)

    try:
        choice = input("🔢 Selection: ").strip()
        if not choice:
            print("✅ Keeping current model.")
            return None

        idx = int(choice) - 1
        if 0 <= idx < len(models):
            selected_model = models[idx].resolve()
            with open(SELECTION_FILE, "w") as f:
                f.write(str(selected_model))
            print(f"✅ Model selected: {selected_model.name}")
            return selected_model
        else:
            print("⚠️ Invalid selection.")
    except ValueError:
        print("⚠️ Invalid input. Enter a number.")
    return None


def get_selected_model():
    if SELECTION_FILE.exists():
        with open(SELECTION_FILE) as f:
            path = f.read().strip()
            if Path(path).exists():
                return path
            else:
                print("⚠️ Selected model file not found. Using default.")
    return str(MODEL_DIR / "zephyr-7b-alpha.Q4_K_M.gguf")


if __name__ == "__main__":
    choose_model()

