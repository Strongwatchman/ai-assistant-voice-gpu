# arc/prompt_formatting.py

def format_prompt(prompt: str, style: str) -> str:
    s = (style or "raw").lower()
    if s == "openchat":
        return f"<|user|>{prompt}<|assistant|>"
    if s == "human_assistant":
        return f"### Human:\n{prompt}\n### Assistant:"
    if s == "im_start":
        return f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant"
    return prompt  # raw
