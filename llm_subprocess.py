import subprocess
import os

# Absolute path to your model
MODEL_PATH = "/home/strongwatchman/AI_Assistant/llama.cpp/models/zephyr/zephyr-7b-alpha.Q4_K_M.gguf"

# Function to query llama-run with subprocess
def query_llm(prompt: str, ngl_layers: int = 24):
    try:
        command = [
            "llama-run",
            "--ngl", str(ngl_layers),
            MODEL_PATH,
            prompt
        ]

        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr.strip()}"

# Example usage
if __name__ == "__main__":
    user_input = "Tell me a little about yourself. You are Mike Boudet of Sword and Scale."
    print(query_llm(user_input))

