# model_switcher.py

import os
import sys

CONFIG_FILE = "config.py"
MODELS_DIR = "./models"

MODEL_REGISTRY = {
    "mythomax": "mythomax-l2-7b.Q4_K_M.gguf",
    "dolphin": "dolphin-2.6-mistral.Q4_0.gguf",
    "zeahermes": "zeahermes-13b.Q4_K_M.gguf",
    "airoboros": "airoboros-l2-7b.Q4_K_M.gguf",
    "openhermes": "openhermes-2.5-mistral.Q4_K_M.gguf",
    "default": "zephyr-7b-alpha.Q4_K_M.gguf",
}

def update_config(model_path):
    with open(CONFIG_FILE, "w") as f:
        f.write("import os\n")
        f.write(f'MODEL_PATH = os.path.abspath("{model_path}")\n')
    print(f"✅ Model switched to: {os.path.basename(model_path)}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python model_switcher.py --use <model_name>")
        print(f"Available models: {', '.join(MODEL_REGISTRY.keys())}")
        sys.exit(1)

    if sys.argv[1] != "--use":
        print("Error: Expected --use argument.")
        sys.exit(1)

    name = sys.argv[2]
    if name not in MODEL_REGISTRY:
        print(f"❌ Model '{name}' not found in registry.")
        print(f"Available: {', '.join(MODEL_REGISTRY.keys())}")
        sys.exit(1)

    model_file = os.path.join(MODELS_DIR, MODEL_REGISTRY[name])
    if not os.path.exists(model_file):
        print(f"❌ Model file not found: {model_file}")
        sys.exit(1)

    update_config(model_file)

if __name__ == "__main__":
    main()
