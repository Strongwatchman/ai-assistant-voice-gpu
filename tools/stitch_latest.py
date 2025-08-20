#!/usr/bin/env python3
import pathlib, glob, os, shutil, subprocess, sys

OUTROOT = pathlib.Path.home()/"AI_Assistant"/"ComfyUI"/"output"/"seed_walk_safe"
runs = sorted([p for p in OUTROOT.glob("*/") if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
if not runs: sys.exit("No seed_walk_safe runs found.")
run_dir = runs[0]
prefix = "seed_walk_safe"

files = sorted(glob.glob(str(run_dir/f"{prefix}_*.png")))
if not files: sys.exit(f"No frames found under {run_dir}")

vid = run_dir/"_vid"
if vid.exists():
    for f in vid.iterdir():
        try: f.unlink()
        except: pass
else:
    vid.mkdir(parents=True, exist_ok=True)

for i, f in enumerate(files, start=1):
    dst = vid / f"frame_{i:05d}.png"
    try:
        os.link(f, dst)
    except OSError:
        shutil.copy2(f, dst)

fps = int(os.environ.get("FPS","8"))
up = os.environ.get("UPSCALE","0")
pattern = str(vid/"frame_%05d.png")
out = run_dir/f"{prefix}.mp4"
cmd = ["ffmpeg","-y","-framerate",str(fps),"-i",pattern]
if up and up != "0": cmd += ["-vf",f"scale={up}:-2"]
cmd += ["-c:v","libx264","-pix_fmt","yuv420p",str(out)]
print("→ ffmpeg:", " ".join(cmd))
subprocess.run(cmd, check=True)
print("🎬", out)
