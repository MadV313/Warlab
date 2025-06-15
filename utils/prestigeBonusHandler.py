# utils/prestigeBonusHandler.py

def get_unlocked_features(prestige_level: int, profile: dict = None) -> list:
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

    # Optional logic for non-prestige bonuses (Dark Ops via raids)
    if profile and profile.get("raidsSuccessful", 0) >= 25:
        bonuses.append("Dark Ops Lab Skin")

    return bonuses

def can_craft_tactical(prestige: int) -> bool:
    return prestige >= 2

def can_craft_explosives(prestige: int) -> bool:
    return prestige >= 3

def can_use_labskins(prestige: int) -> bool:
    return prestige >= 4

def has_full_warlab_unlock(prestige: int) -> bool:
    return prestige >= 5

def has_dark_ops_skin(profile: dict) -> bool:
    """
    Returns True if the user has completed 25 or more successful raids.
    This logic is used to unlock the 'Dark Ops' labskin.
    """
    return profile.get("raidsSuccessful", 0) >= 25
