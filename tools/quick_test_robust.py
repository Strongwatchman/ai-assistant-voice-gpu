#!/usr/bin/env python3
import os, time, socket, requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

COMFY = os.environ.get("COMFY_URL", "http://127.0.0.1:8189")

def wait_for_port(url: str, timeout: int = 60) -> bool:
    hostport = url.split("://", 1)[1].split("/", 1)[0]
    if ":" in hostport:
        host, port = hostport.split(":")
    else:
        host, port = hostport, "80"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, int(port)), timeout=2):
                return True
        except OSError:
            time.sleep(1)
    return False

class NoKeepAliveSession(requests.Session):
    def __init__(self):
        super().__init__()
        self.headers["Connection"] = "close"

retry = Retry(
    total=5,
    connect=5,
    read=5,
    backoff_factor=0.8,
    status_forcelist=[502, 503, 504],
    raise_on_status=False,
)

s = NoKeepAliveSession()
s.mount("http://", HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=4))
s.mount("https://", HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=4))

assert wait_for_port(COMFY, 90), f"ComfyUI not listening at {COMFY}"

# Fetch a valid checkpoint name (retry-safe via 's')
ckpt_info = s.get(f"{COMFY}/object_info/CheckpointLoaderSimple", timeout=10).json()
ckpt = ckpt_info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0][0]

payload = {
    "prompt": {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 1,
                "steps": 8,
                "cfg": 5.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["7", 0],
            },
        },
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ckpt}},
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "test sphere in the desert, sunset, detailed",
                "clip": ["4", 1],
            },
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "lowres, blurry, worst quality, watermark, text",
                "clip": ["4", 1],
            },
        },
        "7": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 384, "height": 256, "batch_size": 1},
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"images": ["8", 0], "filename_prefix": "quick_test"},
        },
    },
    "client_id": "quick-test",
}

resp = s.post(f"{COMFY}/prompt", json=payload, timeout=20)
resp.raise_for_status()
pid = resp.json()["prompt_id"]

deadline = time.time() + 120
last_err = None
while time.time() < deadline:
    time.sleep(1)
    try:
        h = s.get(f"{COMFY}/history/{pid}", timeout=10)
        if h.ok:
            data = h.json()
            if pid in data and "outputs" in data[pid]:
                print("✅ Single frame done. Check ComfyUI/output/")
                break
    except Exception as e:
        last_err = e
        time.sleep(2)
else:
    raise SystemExit(f"Timed out polling /history ({last_err})")
