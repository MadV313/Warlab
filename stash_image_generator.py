# stash_image_generator.py — Composite generator for Fortify UI visuals (Badge fix)

import os
from PIL import Image, ImageEnhance, ImageDraw, ImageFont

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

# === Font for Badge Overlays ===
BADGE_FONT_PATH = "assets/fonts/arialbd.ttf"
BADGE_FONT_SIZE = 26

def generate_stash_image(user_id: str, reinforcements: dict, base_path: str = DEFAULT_LAYERS_DIR, baseImagePath: str = None) -> str:
    """
    Composites a stash image for a user based on equipped reinforcements and custom base image.
    Returns the saved image path.
    """
    output_path = os.path.join(OUTPUT_DIR, f"{user_id}.png")

    if os.path.exists(output_path):
        os.remove(output_path)
        print(f"♻️ Removed cached image to regenerate: {output_path}")

    try:
        # 🔍 Load base image
        if not baseImagePath:
            baseImagePath = os.path.join(base_path, "base_house.png")
        if not os.path.exists(baseImagePath):
            print("⚠️ Missing base image, falling back.")
            baseImagePath = os.path.join(base_path, "base_house.png")
        if not os.path.exists(baseImagePath):
            raise FileNotFoundError(f"❌ Base image not found: {baseImagePath}")

        base = Image.open(baseImagePath).convert("RGBA")
        base_size = base.size
        print(f"🎨 Base size: {base_size}")

        # 🎨 Font for badges
        try:
            font = ImageFont.truetype(BADGE_FONT_PATH, BADGE_FONT_SIZE)
        except:
            font = ImageFont.load_default()
            print("⚠️ Using default font for badges.")

        for key, filename in LAYER_FILES.items():
            readable = key.replace("_", " ").title()
            count = reinforcements.get(readable, 0)
            if count == 0:
                continue

            layer_path = os.path.join(base_path, filename)
            if not os.path.exists(layer_path):
                print(f"⚠️ Missing layer file: {layer_path}")
                continue

            overlay = Image.open(layer_path).convert("RGBA")
            if overlay.size != base_size:
                overlay = overlay.resize(base_size)
                print(f"🔧 Resized {filename} to match base size")

            # 🌟 Composite overlay with base
            faded = ImageEnhance.Brightness(overlay).enhance(1.15)
            base.alpha_composite(faded)

            # 🏷️ Add badge as separate transparent layer if count > 1
            if count > 1:
                badge_text = f"x{count}"
                badge_img = Image.new("RGBA", base_size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(badge_img)

                badge_position = (base_size[0] - 60, 10 + list(LAYER_FILES.keys()).index(key) * 40)
                draw.text(badge_position, badge_text, fill=(255, 255, 0, 255), font=font)
                base.alpha_composite(badge_img)

                print(f"🏷️ Badge {badge_text} drawn at {badge_position}")

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
        "Locked Container": 2,
        "Guard Dog": 1,
        "Claymore Trap": 1
    }

    path = generate_stash_image(
        test_user_id,
        test_reinforcements,
        baseImagePath="assets/stash_layers/base_house_prestige3.png"
    )
    print(f"🖼️ Output: {path}")
