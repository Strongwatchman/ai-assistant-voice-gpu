import os, time, glob, subprocess, requests, pathlib, sys

COMFY = os.environ.get("COMFY_URL", "http://127.0.0.1:8189")
OUT = pathlib.Path.home() / "AI_Assistant" / "ComfyUI" / "output"

def die(msg):
    print(msg)
    sys.exit(1)

# Ping ComfyUI
try:
    r = requests.get(f"{COMFY}/object_info/CheckpointLoaderSimple", timeout=5)
    r.raise_for_status()
except Exception as e:
    die(f"❌ ComfyUI unreachable: {e}")

choices = r.json()["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
ckpt = next((c for c in choices if "v1-5-pruned-emaonly" in c), choices[0])

def run_frame(seed, prompt, w, h, steps, prefix):
    graph = {
      "3":{"class_type":"KSampler","inputs":{"seed":seed,"steps":steps,"cfg":7.0,"sampler_name":"euler","scheduler":"normal","denoise":1.0,"model":["4",0],"positive":["5",0],"negative":["6",0],"latent_image":["7",0]}},
      "4":{"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":ckpt}},
      "5":{"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["4",1]}},
      "6":{"class_type":"CLIPTextEncode","inputs":{"text":"lowres, blurry, worst quality, watermark, text","clip":["4",1]}},
      "7":{"class_type":"EmptyLatentImage","inputs":{"width":640,"height":448,"batch_size":1}},
      "8":{"class_type":"VAEDecode","inputs":{"samples":["3",0],"vae":["4",2]}},
      "9":{"class_type":"SaveImage","inputs":{"images":["8",0],"filename_prefix":prefix}}
    }
    rr = requests.post(f"{COMFY}/prompt", json={"prompt":graph,"client_id":"seedwalk"}, timeout=30)
    rr.raise_for_status()
    pid = rr.json()["prompt_id"]

    # wait for completion and collect files
    while True:
        hh = requests.get(f"{COMFY}/history/{pid}", timeout=30)
        if hh.status_code == 200:
            d = hh.json().get(pid)
            if d and d.get("status",{}).get("completed"):
                outs=[]
                for node in d.get("outputs",{}).values():
                    for im in node.get("images",[]):
                        outs.append(im["filename"])
                return outs
        time.sleep(0.2)

prompt = "surreal greenhouse timelapse, cinematic, dreamy light"
seconds, fps, steps = 3, 10, 14       # quick test: 30 frames
N = seconds * fps
sub = f"greenhouse_walk_{int(time.time())}"
prefix = f"{sub}/frame"
(OUT/sub).mkdir(parents=True, exist_ok=True)

print(f"▶ Frames: {N} -> {OUT/sub}")
seed0 = int(time.time()) & 0x7fffffff
saved = []
for i in range(N):
    outs = run_frame(seed0+i, prompt, 640, 448, steps, prefix)
    outs = [o for o in outs if o.startswith(f"{sub}/")]
    if not outs:
        die(f"❌ No files for frame {i}. Check tmux logs.")
    saved.extend(outs)
    if (i+1) % 5 == 0:
        print(f"  ... {i+1}/{N}")

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
