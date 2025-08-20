# arc/arc_core.py

from arc.config import load_settings
from arc.llm_handler import generate_response
import importlib

def route_prompt(prompt: str) -> str:
    settings = load_settings()
    ark_module_name = settings.get("ark_module")

    if ark_module_name:
        try:
            ark = importlib.import_module(f"ark_modules.{ark_module_name}")
            if hasattr(ark, "respond"):
                return ark.respond(prompt)
            else:
                return f"❌ ARK module '{ark_module_name}' missing `respond()` function."
        except Exception as e:
            return f"❌ Failed to load ARK module '{ark_module_name}': {e}"

    # If no ARK specified, use LLM directly
    return generate_response(prompt)
