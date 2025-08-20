#!/usr/bin/env python3
import os, json, time, random, urllib.request
U=os.environ.get("COMFY_URL","http://127.0.0.1:8189").rstrip("/")
CKPT=os.environ.get("CKPT","realisticVisionV60B1_v51HyperVAE.safetensors")  # default SDXL
LORA=os.environ.get("LORA","")  # leave empty for SD1.5
W,H,STEPS,CFG=576,832,26,6.5
POS="photorealistic portrait, soft studio light, realistic skin, natural eyes"
NEG="lowres, bad anatomy, extra fingers, text, watermark, blur"
def get(p): return urllib.request.urlopen(f"{U}{p}",timeout=10).read()
def post(p,x):
  r=urllib.request.Request(f"{U}{p}",data=json.dumps(x).encode(),headers={"Content-Type":"application/json"})
  return urllib.request.urlopen(r,timeout=30).read()
# build graph
g={}; nid=1; N=lambda: str((nid:=nid+1))
g["1"]={"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":CKPT}}
last_m,last_c="1","1"
if LORA:
  g["2"]={"class_type":"LoraLoader","inputs":{"lora_name":LORA,"strength_model":0.6,"strength_clip":0.6,"model":[last_m,0],"clip":[last_c,1]}}
  last_m,last_c="2","2"
g["3"]={"class_type":"CLIPTextEncode","inputs":{"text":POS,"clip":[last_c,1]}}
g["4"]={"class_type":"CLIPTextEncode","inputs":{"text":NEG,"clip":[last_c,1]}}
g["5"]={"class_type":"EmptyLatentImage","inputs":{"width":W,"height":H,"batch_size":1}}
g["6"]={"class_type":"KSampler","inputs":{
  "seed":random.randint(1,2**31-1),"steps":STEPS,"cfg":CFG,"sampler_name":"euler","scheduler":"normal","denoise":1.0,
  "model":[last_m,0],"positive":["3",0],"negative":["4",0],"latent_image":["5",0]}}
g["7"]={"class_type":"VAEDecode","inputs":{"samples":["6",0],"vae":["1",2]}}
g["8"]={"class_type":"SaveImage","inputs":{"images":["7",0],"filename_prefix":"portrait_min"}}
# post + wait
pid=json.loads(post("/prompt",{"prompt":g})).get("prompt_id")
t=time.time()
while time.time()-t<90:
  try:
    h=json.loads(get(f"/history/{pid}")); 
    if pid in h and "outputs" in h[pid]: break
  except: pass
  time.sleep(1)
print("posted prompt_id:", pid)
