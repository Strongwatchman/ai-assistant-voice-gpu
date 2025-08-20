# ark_modules/ark_apothecary.py

# 🔮 Apothecary Module (Herbs, Tinctures, Remedies)

herbs = {
    "mullein": {
        "uses": [
            "Supports lung and respiratory health",
            "Used in teas and tinctures for dry coughs",
            "Has mild antibacterial and anti-inflammatory properties"
        ],
        "forms": ["Tea", "Tincture", "Smoke (ceremonial)", "Oil infusion"],
        "warnings": ["Avoid if allergic to ragweed family", "Do not use moldy mullein"]
    },
    "pine": {
        "uses": [
            "Rich in vitamin C (needles)",
            "Stimulates immunity and circulation",
            "Used in steam baths or salves for congestion"
        ],
        "forms": ["Needle tea", "Salve", "Essential oil", "Tincture"],
        "warnings": ["Avoid during pregnancy", "Check tree species before harvesting"]
    },
    "echinacea": {
        "uses": [
            "Boosts immune response",
            "Often used at onset of colds or flu",
            "Anti-inflammatory and antiviral properties"
        ],
        "forms": ["Capsules", "Tincture", "Tea"],
        "warnings": ["May cause allergic reactions in sensitive people"]
    }
}

def respond(prompt: str) -> str:
    prompt_lc = prompt.lower()

    for herb_name, data in herbs.items():
        if herb_name in prompt_lc:
            response = f"🌿 {herb_name.capitalize()} —\n"
            response += "💡 Uses:\n" + "\n".join(f" - {use}" for use in data["uses"]) + "\n"
            response += "🧪 Forms:\n" + ", ".join(data["forms"]) + "\n"
            response += "⚠️ Warnings:\n" + "; ".join(data["warnings"])
            return response

    return "🤔 I don't recognize that herb yet. Try asking about mullein, pine, or echinacea."
