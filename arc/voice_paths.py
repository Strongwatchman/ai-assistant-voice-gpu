# arc/voice_paths.py
from __future__ import annotations
from pathlib import Path

# Where we persist the selected voice
VOICE_FILE = Path.home() / ".config" / "arc" / "voice.txt"

def ensure_dir() -> None:
    """Make sure ~/.config/arc exists."""
    VOICE_FILE.parent.mkdir(parents=True, exist_ok=True)

