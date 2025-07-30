from pathlib import Path

# Create a minimal debug version of voice_selector.py
debug_script = Path("/mnt/data/debug_voice_selector.py")
debug_script.write_text("""
print("🟢 Voice selector script has started successfully.")
""")

debug_script.name
