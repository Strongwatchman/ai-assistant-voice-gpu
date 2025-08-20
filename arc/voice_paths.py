from pathlib import Path
VOICE_FILE = Path.home()/'.config'/'arc'/'voice.txt'
def ensure_dir():
    VOICE_FILE.parent.mkdir(parents=True, exist_ok=True)
