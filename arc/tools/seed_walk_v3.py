# seed_walk_v3.py — safe, throttled seed-walk -> frames -> mp4
import os, time, json, subprocess, pathlib, random
import requests

COMFY = os.environ.get("COMFY_URL", "http://127.0.0.1:8189")
OUT_ROOT = pathlib.Path.home() / "AI_Assistant" / "ComfyUI" / "output"

def comfy_ping(timeout=3):
    try:
        r = requests.get(f"{COMFY}/object_info/CheckpointLoaderSimple", timeout=timeout)
        r.raise_for_status()
        return True, r.json()
    except Exception as e:
        return False, e

def resolve_ckpt_name(prefer_substr="v1-5-pruned-emaonly", info=None):
    # object_info structure: {"CheckpointLoaderSimple": {"input": {"required": {"ckpt_name": [[<choices>], {...}]}}}}
    choices = info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    for c in choices:
        if prefer_substr in c:
            return c
    return choices[0]

def submit_and_wait(prompt_graph, max_wait_s=300, poll_s=1.0):
    # 1) queue prompt
    r = requests.post(f"{COMFY}/prompt", json=prompt_graph, timeout=10)
    r.raise_for_status()
    pid = r.json().get("prompt_id")
    if not pid:
        raise RuntimeError("No prompt_id returned.")
    # 2) poll history
    t0 = time.time()
    while True:
        time.sleep(poll_s)
        r2 = requests.get(f"{COMFY}/history/{pid}", timeout=10)
        if r2.ok:
            hist = r2.json()
            # Comfy records outputs at key = pid
            if pid in hist and "outputs" in hist[pid]:
                outs = []
                for node_id, out in hist[pid]["outputs"].items():
                    if "images" in out:
                        for im in out["images"]:
                            # images carry filename and subfolder
                            sub = im.get("subfolder", "")
                            name = im.get("filename")
                            if name:
                                # Path inside ComfyUI/output
                                outs.append(str(OUT_ROOT / sub / name) if sub else str(OUT_ROOT / name))
                return outs
        if time.time() - t0 > max_wait_s:
            raise TimeoutError(f"Prompt {pid} timeout after {max_wait_s}s.")

def txt2img_graph(ckpt_name, text, w, h, steps, seed, prefix):
    return {
        "prompt": {
            "3":{"class_type":"KSampler","inputs":{
                "seed":seed,"steps":steps,"cfg":7.0,
                "sampler_name":"euler","scheduler":"normal","denoise":1.0,
                "model":["4",0],"positive":["5",0],"negative":["6",0],"latent_image":["7",0]
            }},
            "4":{"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name": ckpt_name}},
            "5":{"class_type":"CLIPTextEncode","inputs":{"text":text,"clip":["4",1]}},
            "6":{"class_type":"CLIPTextEncode","inputs":{"text":"lowres, blurry, worst quality, watermark, text","clip":["4",1]}},
            "7":{"class_type":"EmptyLatentImage","inputs":{"width":w,"height":h,"batch_size":1}},
            "8":{"class_type":"VAEDecode","inputs":{"samples":["3",0],"vae":["4",2]}},
            "9":{"class_type":"SaveImage","inputs":{"images":["8",0],"filename_prefix": prefix}}
        },
        "client_id":"seed-walk-v3"
    }

def main():
    ok, info = comfy_ping(timeout=5)
    if not ok:
        raise SystemExit(f"❌ ComfyUI not reachable on {COMFY}: {info}")

    ckpt = resolve_ckpt_name("v1-5-pruned-emaonly", info)
    print("Using ckpt:", ckpt)

    # Settings (keep light for RTX 3050)
    prompt = "surreal greenhouse timelapse, cinematic, dreamy light"
    frames = 24
    fps = 8
    width, height = 512, 384
    steps = 10
    cfg = 6.5
    base_seed = random.randrange(0, 2**31 - 1)

    stamp = str(int(time.time()))
    out_dir = OUT_ROOT / f"greenhouse_walk_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"▶ Frames: {frames} -> {out_dir}")

    saved = 0
    for i in range(frames):
        # Back off a little between frames to avoid thrashing
        time.sleep(0.5)

        # Re-ping before each frame; if server died, bail early
        ok, _ = comfy_ping(timeout=3)
        if not ok:
            print(f"⚠️ ComfyUI appears down before frame {i}. Stopping.")
            break

        seed = base_seed + i
        prefix = f"{out_dir.name}"  # saved under ComfyUI/output/<prefix>_<…>.png
        graph = txt2img_graph(ckpt, prompt, width, height, steps, seed, prefix)

        # Robust submit with simple retry
        for attempt in range(3):
            try:
                outs = submit_and_wait(graph, max_wait_s=300, poll_s=1.0)
                # Filter to our prefix
                outs = [p for p in outs if out_dir.name in p]
                if outs:
                    # Rename into sequential frames we control
                    src = outs[0]
                    dst = out_dir / f"frame_{i:05d}.png"
                    pathlib.Path(src).replace(dst)
                    print(f"✔ Frame {i} -> {dst.name}")
                    saved += 1
                else:
                    print(f"⚠️ Frame {i}: no outputs")
                break
            except Exception as e:
                print(f"⚠️ Frame {i} transient error (attempt {attempt+1}/3): {e}")
                time.sleep(1.5)
        else:
            print(f"❌ Frame {i} failed after retries; continuing.")

    if saved == 0:
        raise SystemExit("❌ No frames saved. Check tmux logs: tmux capture-pane -pt comfy_3050 -S -200 | tail -n 150")

    # Stitch to mp4
    mp4 = OUT_ROOT / f"{out_dir.name}.mp4"
    cmd = [
        "ffmpeg","-y","-framerate", str(fps),
        "-i", str(out_dir / "frame_%05d.png"),
        "-c:v","libx264","-pix_fmt","yuv420p",
        str(mp4)
    ]
    print("▶ ffmpeg:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print("🎬 Video:", mp4)

if __name__ == "__main__":
    main()
