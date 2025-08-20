#!/usr/bin/env python3
import os, sys, time, json, random, difflib, urllib.request, urllib.parse
COMFY_URL=os.environ.get("COMFY_URL","http://127.0.0.1:8189").rstrip("/")
WIDTH,HEIGHT,STEPS,CFG=576,832,26,6.5
LORA_STRENGTH=0.6
DESIRED_CKPT="Deliberate_v6.safetensors"    # change to SDXL ckpt if you want XL LoRAs
DESIRED_LORAS=["PerfectEyesXL.safetensors"] # comment out if using SD 1.5
POS="photorealistic portrait, 35mm, soft studio lighting, realistic skin, natural eyes, subtle makeup, looking at camera"
NEG="lowres, worst quality, bad anatomy, extra fingers, deformed, watermark, text, jpeg artifacts, over/underexposed, blurry, cartoonish"
OUT=os.path.expanduser("~/AI_Assistant/ComfyUI/output")
gget=lambda p: urllib.request.urlopen(f"{COMFY_URL}{p}", timeout=10).read()
def gpost(p, payload):
  r=urllib.request.Request(f"{COMFY_URL}{p}", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
  import urllib.error
  try:
    return urllib.request.urlopen(r, timeout=30).read()
  except urllib.error.HTTPError as e:
    print("SERVER SAYS:", e.read().decode("utf-8","ignore"))
    raise
def wait():
  t=time.time()
  while time.time()-t<45:
    try: gget("/object_info/CheckpointLoaderSimple"); return
    except: time.sleep(1)
  sys.exit("ComfyUI not reachable")
def names(node, field):
  j=json.loads(gget(f"/object_info/{node}")); opt=j[node]["input"]["required"][field][0]; out=[]
  for it in opt:
    if isinstance(it,str): out.append(it)
    elif isinstance(it,(list,tuple)) and it and isinstance(it[0],str): out.append(it[0])
  return out
def best(desired, options):
  if desired in options: return desired
  d=desired.split(".")[0].casefold(); bases=[o.split(".")[0].casefold() for o in options]
  m=difflib.get_close_matches(desired, options, n=1, cutoff=0.55)
  if m: return m[0]
  m2=difflib.get_close_matches(d, bases, n=1, cutoff=0.55)
  if m2: return options[bases.index(m2[0])]
  for i,b in enumerate(bases):
    if b.startswith(d) or d.startswith(b): return options[i]
  raise RuntimeError(f"no match for {desired}")
def graph(ckpt, loras):
  nid=1
  def nxt(): nonlocal nid; nid+=1; return str(nid)
  g={}
  g["1"]={"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":ckpt}}
  last_m,last_c="1","1"
  for ln in loras:
    n=nxt(); g[n]={"class_type":"LoraLoader","inputs":{
      "lora_name":ln,"strength_model":LORA_STRENGTH,"strength_clip":LORA_STRENGTH,"model":[last_m,0],"clip":[last_c,1]}}
    last_m,last_c=n,n
  pos=nxt(); g[pos]={"class_type":"CLIPTextEncode","inputs":{"text":POS,"clip":[last_c,1]}}
  neg=nxt(); g[neg]={"class_type":"CLIPTextEncode","inputs":{"text":NEG,"clip":[last_c,1]}}
  lat=nxt(); g[lat]={"class_type":"EmptyLatentImage","inputs":{"width":WIDTH,"height":HEIGHT,"batch_size":1}}
  ks=nxt(); g[ks]={"class_type":"KSampler","inputs":{
    "seed":random.randint(1,2**31-1),"steps":STEPS,"cfg":CFG,"sampler_name":"euler","scheduler":"normal","denoise":1.0,
    "model":[last_m,0],"positive":[pos,0],"negative":[neg,0],"latent_image":[lat,0]}}
  dec=nxt(); g[dec]={"class_type":"VAEDecode","inputs":{"samples":[ks,0],"vae":["1",2]}}
  final=[dec,0]
  try:
    all_nodes=json.loads(gget("/object_info"))
    keys=[k for k in all_nodes.keys() if "gfpgan" in k.lower()]
    if keys:
      k=keys[0]
      sch=json.loads(gget(f"/object_info/{urllib.parse.quote(k)}"))
      req=set(sch[k]["input"]["required"].keys())
      params={}
      if "image" in req: params["image"]=final
      if "fidelity" in req: params["fidelity"]=0.6
      if "upscale" in req: params["upscale"]=1
      if "tile" in req: params["tile"]=512
      if "tile_overlap" in req: params["tile_overlap"]=16
      gn=nxt(); g[gn]={"class_type":k,"inputs":params}
      final=[gn,0]
  except: pass
  sv=nxt(); g[sv]={"class_type":"SaveImage","inputs":{"images":final,"filename_prefix":"portrait_auto"}}
  return g
def post(g):
  r=json.loads(gpost("/prompt", {"prompt":g})); pid=r.get("prompt_id"); t=time.time(); files=[]
  while time.time()-t<120:
    try:
      h=json.loads(gget(f"/history/{pid}"))
      if pid in h and "outputs" in h[pid]:
        for _,o in h[pid]["outputs"].items():
          for im in o.get("images",[]): 
            fn=im.get("filename"); sub=im.get("subfolder") or ""
            if fn: files.append(os.path.join(OUT, sub, fn))
        if files: break
    except: pass
    time.sleep(1)
  return pid, files
def main():
  wait()
  ckpts=names("CheckpointLoaderSimple","ckpt_name")
  loras=names("LoraLoader","lora_name")
  print("=== ckpts ==="); [print(x) for x in ckpts]
  print("\n=== loras ==="); [print(x) for x in loras]
  ckpt=best(DESIRED_CKPT, ckpts)
  picked=[]
  for d in DESIRED_LORAS:
    try: picked.append(best(d, loras))
    except: pass
  print(f"\n✅ ckpt: {ckpt}")
  if picked: print("✅ loras:"); [print("  -",x) for x in picked]
  pid, out = post(graph(ckpt, picked))
  print(f"\n🧾 prompt_id: {pid}")
  if out: print("💾 saved:"); [print("  -",p) for p in out]
  else: print("⚠️  no files reported yet; open GUI → History")
if __name__=="__main__": main()
