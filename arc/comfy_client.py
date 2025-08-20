# arc/comfy_client.py — minimal, API-correct client for ComfyUI
import os
import time
import requests

COMFY = os.environ.get("COMFY_URL", "http://127.0.0.1:8189")

def comfy_ping(comfy: str = COMFY, timeout: float = 3.0) -> bool:
    """Return True if ComfyUI responds to object_info endpoint."""
    try:
        r = requests.get(f"{comfy}/object_info/CheckpointLoaderSimple", timeout=timeout)
        return r.ok
    except Exception:
        return False

def resolve_ckpt_name(name: str | None, comfy: str = COMFY, timeout: float = 6.0) -> str:
    """
    Return an available ckpt_name. If `name` is provided, match that;
    otherwise return the first available.
    """
    r = requests.get(f"{comfy}/object_info/CheckpointLoaderSimple", timeout=timeout)
    r.raise_for_status()
    js = r.json()
    # ComfyUI returns: {"CheckpointLoaderSimple": {"input": {"required": {"ckpt_name": [[choices...], {...tooltip...}]}}}}
    choices = js["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    if not choices:
        raise RuntimeError("ComfyUI reports no available checkpoints.")
    if not name:
        return choices[0]
    # exact or basename match
    if name in choices:
        return name
    base = name.split("/")[-1]
    for c in choices:
        if c.endswith(base):
            return c
    raise ValueError(f"Requested ckpt '{name}' not found. Available: {choices}")

def build_txt2img_prompt(
    prompt: str,
    width: int = 512,
    height: int = 512,
    steps: int = 20,
    cfg: float = 7.0,
    sampler: str = "euler",
    scheduler: str = "normal",
    seed: int | None = None,
    ckpt_name: str | None = None,
    filename_prefix: str = "ComfyUI_txt2img",
) -> dict:
    """
    Build a simple SD1.5 graph using CheckpointLoaderSimple + KSampler + VAEDecode + SaveImage.
    """
    ckpt = resolve_ckpt_name(ckpt_name, COMFY)
    if seed is None:
        seed = int(time.time()) & 0x7FFFFFFF

    graph = {
        "3": {  # KSampler
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["7", 0],
            },
        },
        "4": {  # CheckpointLoaderSimple
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": ckpt},
        },
        "5": {  # CLIPTextEncode (positive)
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["4", 1]},
        },
        "6": {  # CLIPTextEncode (negative)
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "lowres, blurry, worst quality, watermark, text",
                "clip": ["4", 1],
            },
        },
        "7": {  # EmptyLatentImage
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "8": {  # VAEDecode
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {  # SaveImage
            "class_type": "SaveImage",
            "inputs": {"images": ["8", 0], "filename_prefix": filename_prefix},
        },
    }
    return {"prompt": graph, "client_id": "arc-seed-walk"}

def queue_and_wait(payload: dict, comfy: str = COMFY, poll_s: float = 0.5, max_wait_s: float = 120) -> list[str]:
    """
    POST /prompt then poll /history/{prompt_id} for outputs.
    Returns a list of absolute file paths written by SaveImage.
    """
    r = requests.post(f"{comfy}/prompt", json=payload, timeout=15)
    r.raise_for_status()
    js = r.json()
    prompt_id = js.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"No prompt_id in response: {js}")

    t0 = time.time()
    last_err = None
    while time.time() - t0 < max_wait_s:
        try:
            hh = requests.get(f"{comfy}/history/{prompt_id}", timeout=10)
            if hh.status_code == 404:
                time.sleep(poll_s)
                continue
            hh.raise_for_status()
            hist = hh.json()
            if prompt_id not in hist:
                time.sleep(poll_s)
                continue
            entry = hist[prompt_id]
            if entry.get("status", {}).get("completed"):
                # Collect any SaveImage outputs
                files = []
                for n in entry.get("outputs", {}).values():
                    for img in n.get("images", []):
                        # Comfy returns: {"filename": "...png", "subfolder": "...", "type":"output"}
                        sub = img.get("subfolder","")
                        fn  = img.get("filename","")
                        # Absolute path: <comfy-root>/output/subfolder/filename
                        # Users keep Comfy under ~/AI_Assistant/ComfyUI
                        base = os.path.expanduser("~/AI_Assistant/ComfyUI")
                        out = os.path.join(base, "output", sub, fn) if sub else os.path.join(base, "output", fn)
                        files.append(out)
                return files
        except Exception as e:
            last_err = e
        time.sleep(poll_s)
    if last_err:
        raise last_err
    raise TimeoutError(f"ComfyUI did not finish within {max_wait_s}s.")

# --- compat shim: accept timeout_s like older callers do
try:
    _qaw_real = queue_and_wait  # keep original
    def queue_and_wait(*args, **kwargs):  # override name
        if 'timeout_s' in kwargs and 'max_wait_s' not in kwargs:
            kwargs['max_wait_s'] = kwargs.pop('timeout_s')
        return _qaw_real(*args, **kwargs)
except Exception:
    pass
