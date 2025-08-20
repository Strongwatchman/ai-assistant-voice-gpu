# arc/model_registry.py
# One place to describe prompt style & runtime knobs per model family.

MODEL_CONFIGS = {
    # Core set (good responses)
    "zephyr": {
        "format": "openchat", "context": 2048, "ngl": 28, "temp": 0.7, "top_p": 0.95,
        "path": "zephyr-7b-alpha.Q4_K_M.gguf",
    },
    "openhermes": {
        "format": "im_start", "context": 2048, "ngl": 28, "temp": 0.7, "top_p": 0.95,
        "path": "openhermes-2.5-mistral-7b.Q4_K_M.gguf",
    },
    "dolphin": {
        # NOTE: test runner used im_start and it behaved well; feel free to change to "im_start"
        "format": "openchat", "context": 2048, "ngl": 28, "temp": 0.7, "top_p": 0.95,
        "path": "dolphin-2.6-mistral-7b.Q4_K_M.gguf",
    },
    "mythomist": {
        "format": "openchat", "context": 2048, "ngl": 28, "temp": 0.7, "top_p": 0.95,
        "path": "mythomist-7b.Q4_K_M.gguf",
    },

    # New additions that responded well
    "aura": {
        "format": "raw", "context": 2048, "ngl": 20, "temp": 0.7, "top_p": 0.95,
        "path": "Aura-4B.i1-Q4_K_M.gguf",
    },
    "daybreak": {
        "format": "im_start", "context": 2048, "ngl": 24, "temp": 0.7, "top_p": 0.95,
        "path": "daybreak-kunoichi-2dpo-7b-q4_k_m.gguf",
    },
    "dobby": {
        "format": "human_assistant", "context": 2048, "ngl": 24, "temp": 0.7, "top_p": 0.95,
        "path": "dobby-8b-unhinged-q4_k_m.gguf",
    },
    "stheno_q4": {
        "format": "raw", "context": 2048, "ngl": 24, "temp": 0.7, "top_p": 0.95,
        "path": "L3-8B-Stheno-v3.2-Q4_K_M-imat.gguf",
    },
    "magnum": {
        "format": "raw", "context": 2048, "ngl": 20, "temp": 0.7, "top_p": 0.95,
        "path": "magnum-v2-4b.i1-Q4_0.gguf",
    },
    "spec3b": {
        "format": "raw", "context": 2048, "ngl": 20, "temp": 0.7, "top_p": 0.95,
        "path": "Spec-3b-q4_k_m.gguf",
    },

    # Disabled (too heavy/noisy or we’re pausing usage)
    # "daybreak_q8": {
    #     "format": "im_start", "context": 2048, "ngl": 24, "temp": 0.7, "top_p": 0.95,
    #     "path": "daybreak-kunoichi-2dpo-7b-q8_0.gguf",
    # },
    # "stheno_q8": {
    #     "format": "raw", "context": 2048, "ngl": 28, "temp": 0.7, "top_p": 0.95,
    #     "path": "L3-8B-Stheno-v3.2-Q8_0-imat.gguf",
    # },
    # "specflash": {
    #     "format": "raw", "context": 2048, "ngl": 20, "temp": 0.7, "top_p": 0.95,
    #     "path": "Spec-flash-q4_k_m.gguf",
    # },

    # Previously paused (VRAM/behavior)
    # "airoboros": {
    #     "format":"human_assistant","context":2048,"ngl":28,"temp":0.7,"top_p":0.95,
    #     "path":"airoboros-l2-7B-gpt4-m2.0.Q4_K_M.gguf",
    # },
    # "adventurous": {
    #     "format":"raw","context":2048,"ngl":24,"temp":0.7,"top_p":0.95,
    #     "path":"dans-adventurouswinds-7b.Q4_K_M.gguf",
    # },

    "default": {"format": "raw", "context": 2048, "ngl": 24, "temp": 0.7, "top_p": 0.95},
}

