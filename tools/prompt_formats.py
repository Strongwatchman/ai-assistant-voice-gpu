# arc/prompt_formats.py
from typing import List, Tuple

Chat = List[Tuple[str, str]]  # [("system"|"user"|"assistant", content)]

def build_prompt(fmt: str, chat: Chat) -> str:
    """
    Turn a role-based chat into a single prompt string that matches the selected model's formatting.
    Supported fmt values (from your model_registry): openchat, im_start, human_assistant, raw
    """
    fmt = (fmt or "raw").lower()

    if fmt == "openchat":
        # <|system|> ... <|user|> ... <|assistant|>
        parts = []
        sys = "\n".join(c for r, c in chat if r == "system")
        if sys:
            parts.append(f"<|system|>\n{sys}")
        for role, content in chat:
            if role == "user":
                parts.append(f"<|user|>\n{content}")
            elif role == "assistant":
                parts.append(f"<|assistant|>\n{content}")
        # prompt the assistant to continue
        parts.append("<|assistant|>\n")
        return "\n".join(parts)

    if fmt == "im_start":
        # ChatML style used by OpenHermes/Dolphin variants
        # <|im_start|>system ... <|im_end|>
        parts = []
        for role, content in chat:
            parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")
        # signal assistant turn
        parts.append("<|im_start|>assistant\n")
        return "\n".join(parts)

    if fmt == "human_assistant":
        # Simple "Human:" / "Assistant:" style
        parts = []
        sys = "\n".join(c for r, c in chat if r == "system")
        if sys:
            parts.append(f"System: {sys}")
        for role, content in chat:
            if role == "user":
                parts.append(f"Human: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        parts.append("Assistant: ")
        return "\n".join(parts)

    # default: raw — just show the user content (plus optional system header)
    if fmt == "raw":
        sys = "\n".join(c for r, c in chat if r == "system")
        user = "\n\n".join(c for r, c in chat if r == "user")
        out = ""
        if sys:
            out += f"{sys}\n\n"
        out += user
        return out

    # Fallback if an unknown format sneaks in
    out = []
    for role, content in chat:
        out.append(f"{role.upper()}: {content}")
    out.append("ASSISTANT:")
    return "\n".join(out)

