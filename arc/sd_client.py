import os, base64, time, requests
A1111 = os.environ.get("A1111_URL", "http://127.0.0.1:7860")

def txt2img(prompt, steps=20, w=768, h=512, sampler="Euler a"):
    r = requests.post(f"{A1111}/sdapi/v1/txt2img",
                      json={"prompt": prompt, "steps": steps, "width": w, "height": h, "sampler_name": sampler},
                      timeout=300)
    r.raise_for_status()
    img_b64 = r.json()["images"][0]
    out = f"/tmp/sd_{int(time.time())}.png"
    with open(out, "wb") as f:
        f.write(base64.b64decode(img_b64))
    return out
