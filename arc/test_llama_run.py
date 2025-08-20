import subprocess

prompt = "In one sentence, explain permaculture."
model_path = "/home/strongwatchman/AI_Assistant/llama.cpp/models/zephyr-7b-alpha.Q4_K_M.gguf"

cmd = [
    "/home/strongwatchman/AI_Assistant/llama.cpp/build/bin/llama-run",
    "--context-size", "2048",
    "--ngl", "28",
    "--main-gpu", "0",
    model_path,
    prompt  # ✅ PROMPT GOES AFTER MODEL
]

print("🧠 Running llama-run command (split view):")
for i, part in enumerate(cmd):
    print(f"  [{i}] {part}")
print()

# Run the command and capture output
result = subprocess.run(cmd, capture_output=True, text=True)
print("📤 Output:\n", result.stdout or result.stderr)

