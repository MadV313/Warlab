# utils/inventory.py

from collections import Counter
import random

def has_required_parts(inventory, requirements):
    inv_count = Counter(inventory)
    for item, qty in requirements.items():
        if inv_count[item] < qty:
            return False
    return True

def remove_parts(inventory, requirements):
    for item, qty in requirements.items():
        for _ in range(qty):
            inventory.remove(item)

def weighted_choice(loot_list, rarity_weights):
    """
    Selects one item from a loot list based on rarity weighting.
    Each entry in loot_list must include 'item' and 'rarity'.
    """
    weighted_items = []
    for entry in loot_list:
        rarity = entry["rarity"]
        weight = rarity_weights.get(rarity, 0)
        weighted_items.extend([entry["item"]] * weight)
    return random.choice(weighted_items) if weighted_items else None
