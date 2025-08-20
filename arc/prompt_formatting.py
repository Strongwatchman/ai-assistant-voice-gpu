# arc/prompt_formatting.py
from __future__ import annotations
from typing import List, Tuple

# --- Per-model adjustments copied from the tester ---

FORMAT_OVERRIDES = {
    "dolphin":   "im_start",
    "mythomist": "im_start",
    # kept for reference if re-enabled later:
    "airoboros": "human_assistant",
    "adventurous": "raw",
}

STOP_OVERRIDES = {
    "openhermes": ["<|im_end|>"],
    "dolphin":    ["<|im_end|>"],
    "mythomist":  ["<|im_end|>"],
    # if you re-enable airoboros:
    "airoboros":  ["Human:"],
    # no stop tokens for adventurous (it leaks them)
}

def get_effective_format(model_key: str, registry_format: str | None) -> str:
    """Apply tester’s per-model format overrides on top of registry default."""
    fmt = (registry_format or "raw").lower()
    return FORMAT_OVERRIDES.get(model_key, fmt)

def get_stop_tokens(model_key: str) -> list[str]:
    """Stop tokens that produced clean one-turn completions in the tester."""
    return STOP_OVERRIDES.get(model_key, [])


# ---- Prompt builders (same shapes used in tester) ----

Chat = List[Tuple[str, str]]

def format_prompt(
    user_text: str,
    fmt: str,
    system_text: str = "You are IGOR, a concise and helpful voice assistant.",
) -> str:
    """
    Build a single-turn prompt identical to the tester.
    fmt ∈ {"openchat","im_start","human_assistant","raw"}.
    """
    fmt = (fmt or "raw").lower()

    if fmt == "openchat":
        # <|system|> + <|user|> + <|assistant|>
        parts: list[str] = []
        if system_text:
            parts.append(f"<|system|>\n{system_text}")
        parts.append(f"<|user|>\n{user_text}")
        parts.append("<|assistant|>\n")
        return "\n".join(parts)

    if fmt == "im_start":
        # <|im_start|>system ... <|im_end|> ... then open assistant turn
        parts = [
            f"<|im_start|>system\n{system_text}<|im_end|>",
            f"<|im_start|>user\n{user_text}<|im_end|>",
            "<|im_start|>assistant\n",
        ]
        return "\n".join(parts)

    if fmt == "human_assistant":
        # Human: ... \nAssistant: (open)
        return f"Human: {user_text}\nAssistant: "

    # raw: simple one-liner with an explicit assistant cue
    if fmt == "raw":
        return f"{user_text}\n\nAnswer in two imaginative sentences.\nAssistant:"

    # Fallback
    return f"Human: {user_text}\nAssistant: "

