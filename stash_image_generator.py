# stash_image_generator.py — Composite generator for Fortify UI visuals

import os
from PIL import Image, ImageEnhance

# === Default Paths ===
DEFAULT_LAYERS_DIR = "assets/stash_layers"
OUTPUT_DIR = "generated_stashes"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === Supported Layers in Order (from back to front) ===
LAYER_FILES = {
    "barbed_fence": "barbed_fence.PNG",
    "locked_container": "locked_container.PNG",
    "reinforced_gate": "reinforced_gate.PNG",
    "guard_dog": "guard_dog.PNG",
    "claymore_trap": "claymore_trap.PNG"
}

BASE_IMAGE = "base_house.PNG"

def generate_stash_image(user_id: str, reinforcements: dict, base_path: str = DEFAULT_LAYERS_DIR) -> str:
    """
    Composites a stash image for a user based on their equipped reinforcements.
    Returns the path to the saved image.
    """
    output_path = os.path.join(OUTPUT_DIR, f"{user_id}.png")

    # 🧼 Always regenerate to reflect all reinforcement layers
    if os.path.exists(output_path):
        os.remove(output_path)
        print(f"♻️ Removed cached image to regenerate: {output_path}")

    try:
        base_img_path = os.path.join(base_path, BASE_IMAGE)
        if not os.path.exists(base_img_path):
            raise FileNotFoundError(f"Missing base image: {base_img_path}")

        base = Image.open(base_img_path).convert("RGBA")
        base_size = base.size
        print(f"🎨 Base size: {base_size}")

        for key, filename in LAYER_FILES.items():
            readable_name = key.replace("_", " ").title()
            if reinforcements.get(readable_name, 0) > 0:
                layer_path = os.path.join(base_path, filename)
                if not os.path.exists(layer_path):
                    print(f"⚠️ Missing layer file: {layer_path}")
                    continue

                overlay = Image.open(layer_path).convert("RGBA")
                print(f"📌 Adding: {filename} ({overlay.size})")

                if overlay.size != base_size:
                    overlay = overlay.resize(base_size)
                    print(f"🔧 Resized {key} to match base size")

                faded = ImageEnhance.Brightness(overlay).enhance(1.15)

                # ✅ Composite with alpha masking
                base.alpha_composite(faded)

        base.save(output_path)
        print(f"📦 Saved new stash image: {output_path}")
        return output_path

    except Exception as e:
        print(f"❌ Error generating stash image: {e}")
        return None

# === Local Test ===
if __name__ == "__main__":
    test_user_id = "1234567890"
    test_reinforcements = {
        "Barbed Fence": 3,
        "Reinforced Gate": 1,
        "Locked Container": 1,
        "Guard Dog": 1,
        "Claymore Trap": 1
    }

    path = generate_stash_image(test_user_id, test_reinforcements)
    print(f"🖼️ Output: {path}")
