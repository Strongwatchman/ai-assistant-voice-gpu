import os

# Directory to clean
target_dir = "/home/strongwatchman/AI_Assistant"

# Define file patterns considered temporary
temp_prefixes = ["tmp", "user_input", "output", "response"]
temp_extensions = [".json", ".txt", ".tsv", ".srt", ".vtt", ".wav"]

deleted_files = []

for fname in os.listdir(target_dir):
    full_path = os.path.join(target_dir, fname)
    if os.path.isfile(full_path):
        if any(fname.startswith(p) for p in temp_prefixes) or any(fname.endswith(e) for e in temp_extensions):
            deleted_files.append(fname)
            os.remove(full_path)

if deleted_files:
    print(f"🧹 Deleted {len(deleted_files)} temp files:\n" + "\n".join(deleted_files))
else:
    print("✅ No matching temp files found.")

