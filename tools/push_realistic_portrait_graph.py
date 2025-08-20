#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
push_realistic_portrait_graph.py
- Low-VRAM SD portrait graph poster for ComfyUI (8GB-friendly)
- Verifies server, lists EXACT ckpt/LoRA names, fuzz-maps desired names, posts graph, confirms saved paths.

Usage:
  COMFY_URL="http://127.0.0.1:8189" python ~/AI_Assistant/tools/push_realistic_portrait_graph.py
"""

import os, sys, time, json, random, difflib
import urllib.request, urllib.error

COMFY_URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8189").rstrip("/")

# ----------- Tunables (safe defaults) -----------
DESIRED_CKPT = "Deliberate_v6"   # will fuzzy-match against API list
DESIRED_LORAS = [
    "PerfectEyesXL",
    "NaturalBodyV2.0",
    "Realism Lora By Stable Yogi_V3_Lite",
    "add-detail-xl",
    "SECRET SAUCE B3 Hunyuan",
    "HandFixer",  # the script will fuzzy-match to the exact API filename (e.g., ...Incrs... vs ...lncrs...)
]
LORA_STRENGTH = 0.6  # model & clip strength
WIDTH, HEIGHT = 576, 832
STEPS, CFG = 26, 6.5
SAMPLER_NAME, SCHEDULER = "euler", "normal"
NEGATIVE_PROMPT = (
    "lowres, worst quality, bad anatomy, extra fingers, deformed, watermark, text, jpeg artifacts, "
    "overexposed, underexposed, blurry, cartoonish, painting"
)
POSITIVE_PROMPT = (
    "photorealistic portrait, 35mm, soft studio lighting, sharp details, realistic skin, natural eyes, "
    "subtle makeup, unfiltered look, looking at camera, high quality"
)
OUTPUT_DIR = os.path.expanduser("~/AI_Assistant/ComfyUI/output")

# Optional aliasing if you want to force-map a known typo -> exact file
LORA_ALIASES = {
    # "HandFixer_pdxl_lncrs_v1.safetensors": "HandFixer_pdxl_Incrs_v1.safetensors"
}

# ----------- HTTP helpers -----------
def http_get(path):
    url = f"{COMFY_URL}{path}"
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.read()

def http_post_json(path, payload):
    url = f"{COMFY_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()

def wait_for_server(timeout=45):
    start = time.time()
    while time.time() - start < timeout:
        try:
            http_get("/object_info/CheckpointLoaderSimple")
            return True
        except Exception:
            time.sleep(1)
    return False

# ----------- Introspection -----------
def list_ckpts():
    j = json.loads(http_get("/object_info/CheckpointLoaderSimple"))
    opts = j["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    names = []
    for it in opts:
        if isinstance(it, str):
            names.append(it)
        elif isinstance(it, (list, tuple)) and it and isinstance(it[0], str):
            names.append(it[0])
    return names

def list_loras():
    j = json.loads(http_get("/object_info/LoraLoader"))
    opts = j["LoraLoader"]["input"]["required"]["lora_name"][0]
    names = []
    for it in opts:
        if isinstance(it, str):
            names.append(it)
        elif isinstance(it, (list, tuple)) and it and isinstance(it[0], str):
            names.append(it[0])
    return names

def best_match(desired, options):
    # exact
    if desired in options:
        return desired
    # alias override
    if desired in LORA_ALIASES and LORA_ALIASES[desired] in options:
        return LORA_ALIASES[desired]
    # try by base name (ignore extension/case)
    base = desired.split(".")[0].casefold()
    bases = [o.split(".")[0].casefold() for o in options]
    # close match on full string
    cm = difflib.get_close_matches(desired, options, n=1, cutoff=0.55)
    if cm:
        return cm[0]
    # close match on base
    cm2 = difflib.get_close_matches(base, bases, n=1, cutoff=0.55)
    if cm2:
        idx = bases.index(cm2[0])
        return options[idx]
    # last resort: startswith on base
    for i, b in enumerate(bases):
        if b.startswith(base) or base.startswith(b):
            return options[i]
    raise RuntimeError(f"No reasonable match for '{desired}' in options")

# ----------- Graph builder -----------
def build_graph(ckpt_name, lora_names, seed=None):
    if seed is None:
        seed = random.randint(1, 2**31 - 1)

    nid = 1
    def next_id():
        nonlocal nid
        nid += 1
        return str(nid)

    graph = {}

    # 1) Load checkpoint
    n_ckpt = "1"
    graph[n_ckpt] = {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": ckpt_name}
    }

    # 2) Apply LoRAs sequentially (if any)
    last_model = n_ckpt
    last_clip = n_ckpt
    for ln in lora_names:
        nid_l = next_id()
        graph[nid_l] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": ln,
                "strength_model": LORA_STRENGTH,
                "strength_clip": LORA_STRENGTH,
                "model": [last_model, 0],
                "clip":  [last_clip, 1]
            }
        }
        last_model = nid_l
        last_clip  = nid_l

    # 3) Prompts
    nid_pos = next_id()
    graph[nid_pos] = {"class_type": "CLIPTextEncode",
        "inputs": {"text": POSITIVE_PROMPT, "clip": [last_clip, 1]}
    }
    nid_neg = next_id()
    graph[nid_neg] = {"class_type": "CLIPTextEncode",
        "inputs": {"text": NEGATIVE_PROMPT, "clip": [last_clip, 1]}
    }

    # 4) Latent & KSampler
    nid_lat = next_id()
    graph[nid_lat] = {"class_type": "EmptyLatentImage",
        "inputs": {"width": WIDTH, "height": HEIGHT, "batch_size": 1}
    }

    nid_ks = next_id()
    graph[nid_ks] = {"class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": STEPS,
            "cfg": CFG,
            "sampler_name": SAMPLER_NAME,
            "scheduler": SCHEDULER,
            "denoise": 1.0,omfyUI
            "model": [last_model, 0],
            "positive": [nid_pos, 0],
            "negative": [nid_neg, 0],
            "latent_image": [nid_lat, 0]
        }
    }

    # 5) Decode & save
    nid_decode = next_id()
    graph[nid_decode] = {"class_type": "VAEDecode",
        "inputs": {"samples": [nid_ks, 0], "vae": [n_ckpt, 2]}
    }

    # OPTIONAL: CodeFormer pass (disabled by default)
    # To enable, set USE_CODEFORMER=True and make sure your ComfyUI has CodeFormer nodes installed.
    USE_CODEFORMER = True  # set True only if you know CodeFormerLoader/FaceRestore exist
    if USE_CODEFORMER:
        try:
            # Probe for CodeFormerLoader
            cf = json.loads(http_get("/object_info/CodeFormerLoader"))
            model_names = cf["CodeFormerLoader"]["input"]["required"]["model_name"][0]
            if model_names:
                codeformer_model = model_names[0] if isinstance(model_names[0], str) else model_names[0][0]
                nid_cfl = next_id()
                graph[nid_cfl] = {
                    "class_type": "CodeFormerLoader",
                    "inputs": {"model_name": codeformer_model}
                }
                # FaceRestore node signature may vary slightly by build; this is the common one
                nid_fr = next_id()
                graph[nid_fr] = {
                    "class_type": "FaceRestore",
                    "inputs": {
                        "image": [nid_decode, 0],
                        "fidelity": 0.6,
                        "codeformer": [nid_cfl, 0],
                        "upscale": 1,
                        "provider": "cuda"
                    }
                }
                final_image_src = [nid_fr, 0]
            else:
                final_image_src = [nid_decode, 0]
        except Exception:
            final_image_src = [nid_decode, 0]
    else:
        final_image_src = [nid_decode, 0]

    nid_save = next_id()
    graph[nid_save] = {"class_type": "SaveImage",
        "inputs": {"images": final_image_src, "filename_prefix": "portrait_auto"}
    }

    return graph

def post_and_wait(graph, poll_interval=1.0, max_wait=120):
    # POST /prompt
    resp = json.loads(http_post_json("/prompt", {"prompt": graph}).decode("utf-8"))
    pid = resp.get("prompt_id")
    if not pid:
        raise RuntimeError("No prompt_id returned")

    # Poll /history/<pid>
    start = time.time()
    while time.time() - start < max_wait:
        try:
            h = json.loads(http_get(f"/history/{pid}"))
            # look for saved images
            if h and pid in h and "outputs" in h[pid]:
                outputs = h[pid]["outputs"]
                files = []
                for node_id, out in outputs.items():
                    imgs = out.get("images") or []
                    for im in imgs:
                        fn = im.get("filename")
                        sub = im.get("subfolder") or ""
                        full = os.path.join(OUTPUT_DIR, sub, fn) if fn else None
                        if full:
                            files.append(full)
                if files:
                    return pid, files
        except Exception:
            pass
        time.sleep(poll_interval)
    return pid, []

def main():
    print(f"🔌 Checking ComfyUI at {COMFY_URL} ...")
    if not wait_for_server():
        print("❌ ComfyUI not reachable on /object_info/CheckpointLoaderSimple. Is it running?")
        sys.exit(2)

    # List exact names
    ckpts = list_ckpts()
    loras = list_loras()
    print("\n=== EXACT Checkpoints from API ===")
    for n in ckpts: print(n)
    print("\n=== EXACT LoRAs from API ===")
    for n in loras: print(n)

    # Pick best-match ckpt
    try:
        ckpt_pick = best_match(DESIRED_CKPT, ckpts)
    except Exception as e:
        print(f"\n❌ Couldn't match checkpoint '{DESIRED_CKPT}': {e}")
        sys.exit(3)

    # Pick best-match loras (silently skip ones not found)
    picked_loras = []
    for d in DESIRED_LORAS:
        try:
            picked = best_match(d, loras)
            if picked not in picked_loras:
                picked_loras.append(picked)
        except Exception:
            # just skip if truly not matchable
            pass

    print(f"\n✅ Using ckpt: {ckpt_pick}")
    if picked_loras:
        print("✅ Using LoRAs:")
        for x in picked_loras: print(f"  - {x}")
    else:
        print("⚠️  No LoRAs matched; proceeding without LoRAs.")

    graph = build_graph(ckpt_pick, picked_loras)
    pid, files = post_and_wait(graph)

    print(f"\n🧾 Prompt ID: {pid}")
    if files:
        print("💾 Saved image(s):")
        for f in files:
            print("  -", f)
    else:
        print("⚠️ No files found in /history yet. Open the GUI → History and load the run; outputs should appear under:")
        print("   ", OUTPUT_DIR)

if __name__ == "__main__":
    main()

