# utils/prestigeBonusHandler.py

def get_unlocked_features(prestige_level: int) -> list:
    bonuses = []

    if prestige_level >= 1:
        bonuses.append("Blueprint Access")
    if prestige_level >= 2:
        bonuses.append("Craft Tactical Gear")
    if prestige_level >= 3:
        bonuses.append("Craft Explosives & Special Items")
    if prestige_level >= 4:
        bonuses.append("Unlock Labskins")
    if prestige_level >= 5:
        bonuses.append("Warlab Exclusive Loot")

    return bonuses

def can_craft_tactical(prestige: int) -> bool:
    return prestige >= 2

def can_craft_explosives(prestige: int) -> bool:
    return prestige >= 3

def can_use_labskins(prestige: int) -> bool:
    return prestige >= 4

def has_full_warlab_unlock(prestige: int) -> bool:
    return prestige >= 5
