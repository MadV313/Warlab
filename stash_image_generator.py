# stash_image_generator.py — Composite generator for Fortify UI visuals

import os
import json
from PIL import Image, ImageEnhance

# === Default Paths ===
DEFAULT_LAYERS_DIR = "assets/stash_layers"
OUTPUT_DIR = "generated_stashes"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === Supported Layers in Order (from back to front) ===
LAYER_FILES = {
    "barbed_fence": "barbed_fence.png",
    "locked_container": "locked_container.png",
    "reinforced_gate": "reinforced_gate.png",
    "guard_dog": "guard_dog.png",
    "claymore_trap": "claymore_trap.png"
}

BASE_IMAGE = "base_house.png"

def generate_stash_image(user_id: str, reinforcements: dict, base_path: str = DEFAULT_LAYERS_DIR) -> str:
    """
    Composites a stash image for a user based on their equipped reinforcements.
    Returns the path to the saved image.
    """
    output_path = os.path.join(OUTPUT_DIR, f"{user_id}.png")

    # Caching: Skip if already exists
    if os.path.exists(output_path):
        print(f"✅ Using cached stash image for {user_id}")
        return output_path

    try:
        base = Image.open(os.path.join(base_path, BASE_IMAGE)).convert("RGBA")

        for key in LAYER_FILES:
            readable_name = key.replace("_", " ").title()
            count = reinforcements.get(readable_name, 0)
            if count > 0:
                layer_path = os.path.join(base_path, LAYER_FILES[key])
                if not os.path.exists(layer_path):
                    print(f"⚠️ Missing layer file: {layer_path}")
                    continue

                overlay = Image.open(layer_path).convert("RGBA")

                # Optional: Add animation effects like glow or opacity fade-in
                fade = ImageEnhance.Brightness(overlay).enhance(1.15)
                base = Image.alpha_composite(base, fade)

        base.save(output_path)
        print(f"📦 Saved new stash image: {output_path}")
        return output_path

    except Exception as e:
        print(f"❌ Error generating stash image: {e}")
        return None


# === Example Local Test ===
if __name__ == "__main__":
    test_user_id = "1234567890"
    test_reinforcements = {
        "Barbed Fence": 3,
        "Reinforced Gate": 1,
        "Locked Container": 1,
        "Guard Dog": 1,
        "Claymore Trap": 1
    }

    img_path = generate_stash_image(test_user_id, test_reinforcements)
    print(f"🖼️ Generated: {img_path}")
