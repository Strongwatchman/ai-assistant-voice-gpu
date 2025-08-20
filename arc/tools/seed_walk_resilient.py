import os, time, glob, subprocess, requests, pathlib, sys, random

COMFY = os.environ.get("COMFY_URL", "http://127.0.0.1:8189")
OUT   = pathlib.Path.home() / "AI_Assistant" / "ComfyUI" / "output"

def die(msg):
    print(msg)
    sys.exit(1)

# ---------- small helper with retry ----------
def get_json(url, timeout=10, tries=5, sleep=0.5):
    for k in range(tries):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if k == tries - 1:
                raise
            time.sleep(sleep)
    raise RuntimeError("unreachable")  # not expected

# ---------- ping + choose ckpt once ----------
try:
    info = get_json(f"{COMFY}/object_info/CheckpointLoaderSimple", timeout=5)
except Exception as e:
    die(f"❌ ComfyUI unreachable: {e}")

choices = info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
ckpt = next((c for c in choices if "v1-5-pruned-emaonly" in c), choices[0])
print("Using ckpt:", ckpt)

# ---------- one “graph template” (model loaded once and cached by Comfy) ----------
def build_graph(seed, prompt, w, h, steps, prefix):
    return {
      "3":{"class_type":"KSampler","inputs":{
          "seed":seed,"steps":steps,"cfg":7.0,
          "sampler_name":"euler_a","scheduler":"normal",
          "denoise":1.0,"model":["4",0],
          "positive":["5",0],"negative":["6",0],
          "latent_image":["7",0]}},
      "4":{"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":ckpt}},
      "5":{"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["4",1]}},
      "6":{"class_type":"CLIPTextEncode","inputs":{"text":"lowres, blurry, worst quality, watermark, text","clip":["4",1]}},
      "7":{"class_type":"EmptyLatentImage","inputs":{"width":w,"height":h,"batch_size":1}},
      "8":{"class_type":"VAEDecode","inputs":{"samples":["3",0],"vae":["4",2]}},
      "9":{"class_type":"SaveImage","inputs":{"images":["8",0],"filename_prefix":prefix}}
    }

session = requests.Session()

def run_one_frame(seed, prompt, w, h, steps, prefix):
    payload = {"prompt": build_graph(seed, prompt, w, h, steps, prefix),
               "client_id":"seedwalk"}
    # post with retry (server can hiccup on OOM)
    for k in range(3):
        try:
            rr = session.post(f"{COMFY}/prompt", json=payload, timeout=30)
            rr.raise_for_status()
            pid = rr.json()["prompt_id"]
            break
        except Exception as e:
            if k == 2:
                raise
            time.sleep(0.6)

    # poll history, but be gentle + tolerate resets
    last_err = None
    for _ in range(240):   # up to ~60s
        try:
            hh = session.get(f"{COMFY}/history/{pid}", timeout=10)
            if hh.status_code == 200:
                d = hh.json().get(pid)
                if d and d.get("status",{}).get("completed"):
                    outs=[]
                    for node in d.get("outputs",{}).values():
                        for im in node.get("images",[]):
                            outs.append(im["filename"])
                    return outs
        except requests.exceptions.RequestException as e:
            last_err = e
            # back off a bit; don’t crash on single reset
            time.sleep(0.5)
        time.sleep(0.25)
    raise RuntimeError(f"Timeout or repeated resets while waiting for frame. Last error: {last_err}")

def main():
    prompt = "surreal greenhouse timelapse, cinematic, dreamy light"
    # keep it small first; increase later
    seconds, fps, steps = 3, 8, 12         # 24 frames
    w, h = 640, 448
    seed0 = random.randint(0, 2**31-1)

    sub = f"greenhouse_walk_{int(time.time())}"
    prefix = f"{sub}/frame"
    (OUT/sub).mkdir(parents=True, exist_ok=True)
    print(f"▶ Frames: {seconds*fps} -> {OUT/sub}")

    saved = []
    for i in range(seconds*fps):
        try:
            outs = run_one_frame(seed0+i, prompt, w, h, steps, prefix)
            outs = [o for o in outs if o.startswith(f"{sub}/")]
            if not outs:
                die(f"❌ No files from SaveImage for frame {i}. Check tmux logs.")
            saved.extend(outs)
            if (i+1) % 4 == 0:
                print(f"  ... {i+1}/{seconds*fps}")
        except Exception as e:
            # If we lose connection once, try to ensure server is still up
            try:
                get_json(f"{COMFY}/object_info/CheckpointLoaderSimple", timeout=5, tries=2)
            except Exception:
                die(f"❌ ComfyUI looks down after frame {i}. See tmux logs. Error: {e}")
            # otherwise, continue to next frame (skip this one)
            print(f"⚠️ Skipping frame {i} due to transient error: {e}")
            time.sleep(0.8)

    # ffmpeg → MP4
    pattern = str((OUT/sub)/"frame_%05d_.png")
    if not glob.glob(str((OUT/sub)/"frame_*_.png")):
        pattern = str((OUT/sub)/"frame_%05d.png")
    mp4 = OUT / f"{sub}.mp4"
    cmd = ["ffmpeg","-y","-framerate",str(fps),"-i",pattern,"-c:v","libx264","-pix_fmt","yuv420p",str(mp4)]
    print("▶ ffmpeg:", " ".join(cmd))
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(p.stdout)

    if mp4.exists() and mp4.stat().st_size > 0:
        print("✅ VIDEO:", mp4)
        print("🖼  FRAMES:", len(saved))
    else:
        die("❌ ffmpeg did not create the MP4. Check pattern & folder.")

if __name__ == "__main__":
    main()
