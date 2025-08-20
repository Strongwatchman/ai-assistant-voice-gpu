from pathlib import Path
import os, time, subprocess

from arc.comfy_client import build_txt2img_prompt, queue_and_wait, comfy_ping

def main():
    if not comfy_ping():
        raise SystemExit("❌ ComfyUI not reachable on COMFY_URL")

    out_root = Path.home()/"AI_Assistant"/"ComfyUI"/"output"
    out_root.mkdir(parents=True, exist_ok=True)
    run_id = int(time.time())
    out_dir = out_root / f"greenhouse_walk_{run_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"▶ Frames: 24 -> {out_dir}")

    prompt = "surreal greenhouse timelapse, cinematic, dreamy light"
    steps  = 10
    width, height = 384, 256      # small & stable on 3050
    cfg = 7.0
    seed0 = 1000
    frames = 24

    saved = []
    for i in range(frames):
        seed = seed0 + i
        try:
            payload = build_txt2img_prompt(prompt=prompt, width=width, height=height, steps=steps, cfg=cfg, seed=seed)
            outs = queue_and_wait(payload)   # no timeout_s
            outs = [p for p in outs if p.endswith(".png")]
            if outs:
                # copy/rename sequentially into out_dir
                dst = out_dir / f"frame_{i:05d}.png"
                subprocess.run(["cp", outs[0], str(dst)], check=True)
                saved.append(str(dst))
            else:
                print(f"⚠️ No output for frame {i}, continuing.")
        except Exception as e:
            print(f"⚠️ Transient error on frame {i}: {e}")

    if not saved:
        print("❌ No frames saved. Check tmux logs: tmux capture-pane -pt comfy_3050 -S -200 | tail -n 120")
        return

    # Build mp4
    mp4 = out_dir.with_suffix(".mp4")
    cmd = [
        "ffmpeg","-y","-framerate","8",
        "-i", str(out_dir / "frame_%05d.png"),
        "-c:v","libx264","-pix_fmt","yuv420p", str(mp4)
    ]
    print("▶ ffmpeg:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print("🎬 Video:", mp4)

if __name__ == "__main__":
    main()
