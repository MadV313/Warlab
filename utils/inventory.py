
# utils/inventory.py

from collections import Counter

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
