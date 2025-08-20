#!/usr/bin/env python3
# tools/audit_repo.py — safe report of tree health (sizes, suspicious names, models, tracked files)

import os, re, sys, subprocess, shutil
from pathlib import Path

ROOT = Path.home() / "AI_Assistant"
THRESH_MB = float(os.getenv("AUDIT_LARGE_MB", "20"))

BACKUP_PAT = re.compile(r"(working\s*copy|backup|\.bak|\.old|\.orig)", re.I)
MODEL_EXTS = {".gguf", ".pt", ".safetensors", ".ckpt", ".onnx"}
MEDIA_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".mp4", ".mkv", ".avi", ".gif", ".webm"}
IGNORE_DIRS = {".git", ".venv", "venv", "venv310", "venv_sadtalker", "__pycache__", "build", "dist"}
SKIP_DIRS = {"llama.cpp/build"}

def sizeof_fmt(n):
    for unit in ["B","KB","MB","GB","TB"]:
        if n < 1024: return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"

def git_tracked():
    try:
        out = subprocess.check_output(["git","ls-files"], cwd=ROOT, text=True)
        return set(line.strip() for line in out.splitlines() if line.strip())
    except Exception:
        return set()

def main():
    if not ROOT.exists():
        print(f"❌ Root not found: {ROOT}")
        sys.exit(2)

    tracked = git_tracked()
    large = []
    backups = []
    models = []
    media = []
    other = []
    total_bytes = 0

    for path in ROOT.rglob("*"):
        try:
            rel = path.relative_to(ROOT)
        except Exception:
            continue

        # Skip some heavy trees quickly
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if rel.parts and rel.parts[0] in IGNORE_DIRS:
            continue

        if path.is_file():
            try:
                size = path.stat().st_size
            except Exception:
                continue
            total_bytes += size
            ext = path.suffix.lower()

            # categories
            if BACKUP_PAT.search(path.name):
                backups.append((size, rel))
            elif ext in MODEL_EXTS:
                models.append((size, rel))
            elif ext in MEDIA_EXTS:
                media.append((size, rel))
            else:
                other.append((size, rel))

            if size >= THRESH_MB * 1024 * 1024:
                large.append((size, rel))

    def show(title, items, limit=None):
        print(f"\n# {title} ({len(items)})")
        items = sorted(items, key=lambda x: x[0], reverse=True)
        if limit: items = items[:limit]
        for sz, rel in items:
            mark = " (TRACKED)" if str(rel) in tracked else ""
            print(f"  {sizeof_fmt(sz):>8}  {rel}{mark}")

    print(f"📁 Root: {ROOT}")
    print(f"📦 Total bytes scanned: {sizeof_fmt(total_bytes)}")
    print(f"🧪 Threshold for 'large': ≥ {THRESH_MB} MB")

    show("LARGEST FILES", large, limit=30)
    show("BACKUP / WORKING-COPY SUSPECTS", backups, limit=50)
    show("MODEL-LIKE FILES", models, limit=50)
    show("MEDIA / AUDIO / VIDEO", media, limit=50)

    # short tracked summary
    print("\n# GIT TRACKED SUMMARY")
    if not tracked:
        print("  (git not initialized here or no tracked files)")
    else:
        tracked_large = [(sz, rel) for (sz, rel) in large if str(rel) in tracked]
        if tracked_large:
            print("  ⚠️ Large files IN GIT:")
            for sz, rel in tracked_large:
                print(f"    {sizeof_fmt(sz):>8}  {rel}")
        else:
            print("  No large files tracked. 👍")

    print("\n✅ Audit complete. No changes made.")
    print("Tip: set AUDIT_LARGE_MB=10 to tighten the large-file threshold.")

if __name__ == "__main__":
    main()

