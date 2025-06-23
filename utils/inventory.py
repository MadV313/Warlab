# utils/inventory.py — With persistent-ready structure

from collections import Counter
import random
from utils.fileIO import load_file, save_file  # 📦 Add persistent support if needed later

def has_required_parts(user_parts: dict, requirements: dict) -> bool:
    """
    Check if the player has enough of each required part.
    """
    for part, required_qty in requirements.items():
        if user_parts.get(part, 0) < required_qty:
            return False
    return True

def remove_parts(user_parts: dict, requirements: dict):
    """
    Deduct the required parts from the player's part inventory.
    """
    for part, qty in requirements.items():
        if part in user_parts:
            user_parts[part] -= qty
            if user_parts[part] <= 0:
                del user_parts[part]

def weighted_choice(loot_list, rarity_weights):
    """
    Selects one item (full dict) from a loot list based on rarity weighting.
    Each entry in loot_list must include 'item' and 'rarity'.
    """
    weighted_items = []
    for entry in loot_list:
        rarity = entry["rarity"]
        weight = rarity_weights.get(rarity, 0)
        weighted_items.extend([entry] * weight)  # Append full entry, not just name
    return random.choice(weighted_items) if weighted_items else None
