#!/usr/bin/env python3
import os, time, socket, argparse, requests, sys, pathlib, glob, subprocess, shutil
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HOME = pathlib.Path.home()
OUTROOT = HOME / "AI_Assistant" / "ComfyUI" / "output"
COMFY = os.environ.get("COMFY_URL","http://127.0.0.1:8189")

PRESETS = {
  "portrait": {
    "pos": "photorealistic portrait, natural skin texture, 85mm lens, f/2, catchlights, sharp eyes, cinematic grading",
    "neg": "lowres, blurry, watermark, text, overprocessed skin, deformed hands, extra fingers"
  },
  "interior": {
    "pos": "sunlit greenhouse interior, lush plants, glass roof, golden hour volumetric god rays, cinematic wide shot, highly detailed",
    "neg": "lowres, blurry, oversaturated, watermark, text"
  },
  "product": {
    "pos": "sleek smartwatch on white marble, soft studio lighting, 3-point lighting, photorealistic, sharp focus, product hero shot",
    "neg": "dust, fingerprints, watermark, text, lowres"
  },
  "character": {
    "pos": "retro robot barista, copper and brass, cozy cafe, warm ambient lighting, depth of field, concept art, highly detailed",
    "neg": "blurry, noisy, watermark, text"
  }
}

def wait_for_port(url, secs=90):
    host,port=url.split("://",1)[1].split("/",1)[0].split(":")
    end=time.time()+secs
    while time.time()<end:
        try: socket.create_connection((host,int(port)),2).close(); return True
        except OSError: time.sleep(1)
    sys.exit(f"ComfyUI not reachable at {url}")

def new_session():
    s=requests.Session()
    s.headers["Connection"]="close"
    retry=Retry(total=6, connect=6, read=6, backoff_factor=0.8,
                status_forcelist=[502,503,504], raise_on_status=False)
    a=HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=4)
    s.mount("http://",a); s.mount("https://",a)
    return s

def _names_from_opt(opt):
    names=[]
    for item in opt:
        if isinstance(item,str): names.append(item)
        elif isinstance(item,(list,tuple)) and item and isinstance(item[0],str): names.append(item[0])
    return names

def resolve_ckpt(s, wanted):
    if not wanted: return None
    r=s.get(f"{COMFY}/object_info/CheckpointLoaderSimple", timeout=10); r.raise_for_status()
    names=_names_from_opt(r.json()["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0])
    for n in names:
        if n==wanted or wanted.lower() in n.lower(): return n
    print("⚠️ Requested ckpt not found. First few:", *names[:8], sep="\n - ")
    return None

def default_ckpt(s):
    r=s.get(f"{COMFY}/object_info/CheckpointLoaderSimple", timeout=10); r.raise_for_status()
    opt=r.json()["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    return opt[0] if isinstance(opt[0],str) else opt[0][0]

def resolve_lora(s, wanted):
    if not wanted: return None
    r=s.get(f"{COMFY}/object_info/LoraLoader", timeout=10); r.raise_for_status()
    names=_names_from_opt(r.json()["LoraLoader"]["input"]["required"]["lora_name"][0])
    for n in names:
        if n==wanted or wanted.lower() in n.lower(): return n
    print("⚠️ Requested LoRA not found. First few:", *names[:8], sep="\n - ")
    return None

def post(s, prompt):
    r=s.post(f"{COMFY}/prompt", json=prompt, timeout=60)
    if not r.ok:
        try: print("Server said:", r.text[:400], file=sys.stderr)
        except Exception: pass
        r.raise_for_status()
    return r.json()["prompt_id"]

def build_payload(ckpt_name, lora_name, lora_w, seed, args, prefix_for_save):
    # Base loader
    nodes = {
      "4":{"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":ckpt_name}},
      "7":{"class_type":"EmptyLatentImage","inputs":{"width":args.width,"height":args.height,"batch_size":1}}
    }

    # If LoRA, insert LoraLoader node "10" and route model/clip through it
    if lora_name:
        nodes["10"]={"class_type":"LoraLoader","inputs":{
            "model":["4",0], "clip":["4",1], "lora_name":lora_name,
            "strength_model":lora_w, "strength_clip":lora_w
        }}
        model_ref=["10",0]; clip_ref=["10",1]
    else:
        model_ref=["4",0]; clip_ref=["4",1]

    # Encoders depend on clip_ref
    nodes["5"]={"class_type":"CLIPTextEncode","inputs":{"text":args.positive,"clip":clip_ref}}
    nodes["6"]={"class_type":"CLIPTextEncode","inputs":{"text":args.negative,"clip":clip_ref}}

    # Sampler uses model_ref and encoders
    nodes["3"]={"class_type":"KSampler","inputs":{
        "seed":seed,"steps":args.steps,"cfg":args.cfg,
        "sampler_name":args.sampler,"scheduler":args.scheduler,"denoise":1.0,
        "model":model_ref,"positive":["5",0],"negative":["6",0],"latent_image":["7",0]}}

    # VAE decode
    if args.tiled_vae:
        nodes["8"]={"class_type":"VAEDecodeTiled","inputs":{
            "samples":["3",0],"vae":["4",2],
            "tile_size":args.tile_size,"overlap":args.tile_overlap,
            "temporal_size":max(8,args.temporal_size),
            "temporal_overlap":max(4,args.temporal_overlap),
            "fast_decoder":True,"fp16":True}}
    else:
        nodes["8"]={"class_type":"VAEDecode","inputs":{"samples":["3",0],"vae":["4",2]}}

    # Save
    nodes["9"]={"class_type":"SaveImage","inputs":{"images":["8",0],"filename_prefix":prefix_for_save}}

    return {"prompt":nodes,"client_id":"seed-walk-safe"}

def stitch(run_dir, prefix_leaf, fps, upscale):
    files=sorted(glob.glob(str(run_dir/f"{prefix_leaf}_*.png")))
    if not files: raise RuntimeError("No frames found to stitch.")
    vid=run_dir/"_vid"
    if vid.exists():
        for f in vid.iterdir():
            try: f.unlink()
            except: pass
    else:
        vid.mkdir(parents=True, exist_ok=True)
    for i,f in enumerate(files, start=1):
        dst=vid/f"frame_{i:05d}.png"
        try: os.link(f,dst)
        except OSError: shutil.copy2(f,dst)
    pattern=str(vid/"frame_%05d.png")
    out_path=run_dir/f"{prefix_leaf}.mp4"
    cmd=["ffmpeg","-y","-framerate",str(fps),"-i",pattern]
    if upscale: cmd+=["-vf",f"scale={upscale}:-2"]
    cmd+=["-c:v","libx264","-pix_fmt","yuv420p",str(out_path)]
    print("→ ffmpeg:"," ".join(cmd)); subprocess.run(cmd, check=True)
    print("🎬 Video:", out_path); return out_path

def main():
    p=argparse.ArgumentParser(description="ComfyUI seed-walk (low VRAM) + auto-stitch + ckpt + lora + presets")
    p.add_argument("--frames", type=int, default=36)
    p.add_argument("--width", type=int, default=768)
    p.add_argument("--height", type=int, default=432)
    p.add_argument("--steps", type=int, default=18)
    p.add_argument("--cfg", type=float, default=4.5)
    p.add_argument("--sampler", default="euler")
    p.add_argument("--scheduler", default="normal")
    p.add_argument("--seed", type=int, default=12345)
    p.add_argument("--seed-step", type=int, default=101, dest="seed_step")
    p.add_argument("--delay", type=float, default=1.0)
    p.add_argument("--positive", default="high quality, detailed, cinematic light")
    p.add_argument("--negative", default="lowres, blurry, watermark, text, worst quality")
    p.add_argument("--preset", choices=list(PRESETS.keys()))
    p.add_argument("--ckpt", default=None, help="Checkpoint name (substring match ok)")
    p.add_argument("--lora", default=None, help="LoRA name (substring match ok)")
    p.add_argument("--lora-weight", type=float, default=0.7, dest="lora_weight")
    p.add_argument("--prefix", default=None)
    p.add_argument("--tiled-vae", action="store_true")
    p.add_argument("--tile-size", type=int, default=256, dest="tile_size")
    p.add_argument("--tile-overlap", type=int, default=32, dest="tile_overlap")
    p.add_argument("--temporal-size", type=int, default=64, dest="temporal_size")
    p.add_argument("--temporal-overlap", type=int, default=8, dest="temporal_overlap")
    p.add_argument("--out-video", action="store_true")
    p.add_argument("--fps", type=int, default=8)
    p.add_argument("--upscale", type=int, default=0)
    p.add_argument("--wait-mins", type=float, default=20.0)
    args=p.parse_args()

    if args.preset:
        pr=PRESETS[args.preset]
        if args.positive==p.get_default("positive"): args.positive=pr["pos"]
        if args.negative==p.get_default("negative"): args.negative=pr["neg"]

    wait_for_port(COMFY,90)
    s=new_session()
    ck = resolve_ckpt(s, args.ckpt) or default_ckpt(s)
    lr = resolve_lora(s, args.lora) if args.lora else None

    run_id=time.strftime("%Y%m%d_%H%M%S")
    if args.prefix:
        run_dir=OUTROOT / pathlib.Path(args.prefix).parent
        prefix_leaf=pathlib.Path(args.prefix).name
        prefix_for_save=args.prefix
    else:
        run_dir=OUTROOT/"seed_walk_safe"/run_id; run_dir.mkdir(parents=True, exist_ok=True)
        prefix_leaf="seed_walk_safe"; prefix_for_save=f"seed_walk_safe/{run_id}/{prefix_leaf}"

    print("Starting seed walk with:", {**vars(args), "ckpt": ck, "lora": lr, "prefix_resolved": prefix_for_save})
    for i in range(args.frames):
        s_val=args.seed + i*args.seed_step
        pid=post(s, build_payload(ck, lr, args.lora_weight, s_val, args, prefix_for_save))
        print(f"  • queued frame {i+1}/{args.frames} (seed={s_val}, pid={pid})")
        time.sleep(args.delay)
    print("Queued. Output dir:", run_dir)

    if not args.out_video: return
    want=args.frames; deadline=time.time()+args.wait_mins*60
    pattern=str(run_dir/f"{prefix_leaf}_*.png")
    while time.time()<deadline and not glob.glob(pattern): time.sleep(1)
    while time.time()<deadline and len(glob.glob(pattern))<want: time.sleep(1)
    files=glob.glob(pattern)
    if not files: print("⚠️ No frames found to stitch.", file=sys.stderr); return
    try:
        stitch(run_dir, prefix_leaf, args.fps, args.upscale if args.upscale>0 else None)
    except subprocess.CalledProcessError as e:
        print("ffmpeg failed:", e, file=sys.stderr)

if __name__=="__main__": main()
