# utils/prestigeUtils.py — Centralized Prestige Rank System

from utils.boosts import is_weekend_boost_active

PRESTIGE_TIERS = {
    1: 200,     # Prestige I
    2: 400,     # Prestige II
    3: 600,     # Prestige III
    4: 800,     # Prestige IV (Lab Skins Unlock)
    5: 1000     # Prestige V (Special Unlocks)
}

PRESTIGE_CLASSES = {
    1: {"title": "☣️ Raider Elite", "color": 0x880808},
    2: {"title": "💉 Weaponsmith Elite", "color": 0x88e0a0},
    3: {"title": "🔬 Scavenger Elite", "color": 0x3cb4fc},
}

def get_prestige_rank(points: int) -> int:
    for rank in sorted(PRESTIGE_TIERS.keys(), reverse=True):
        if points >= PRESTIGE_TIERS[rank]:
            return rank
    return 0

def get_prestige_progress(points: int) -> dict:
    current_rank = get_prestige_rank(points)
    next_rank = current_rank + 1
    current_threshold = PRESTIGE_TIERS.get(current_rank, 0)
    next_threshold = PRESTIGE_TIERS.get(next_rank)

    return {
        "current_rank": current_rank,
        "points": points,
        "current_threshold": current_threshold,
        "next_threshold": next_threshold,
        "points_to_next": (next_threshold - points) if next_threshold else None
    }

def get_prestige_class(user: dict):
    skin = user.get("skin")
    raids = user.get("successful_raids", 0)
    blueprints = user.get("blueprints", [])
    scavenges = user.get("scavenges_completed", 0)

    if skin == "Dark Ops" and raids >= 25:
        return PRESTIGE_CLASSES[1]
    elif skin == "Architect's Vault" and len(blueprints) >= 12:
        return PRESTIGE_CLASSES[2]
    elif skin == "Scavenger's Haven" and scavenges >= 100:
        return PRESTIGE_CLASSES[3]
    return None

def apply_prestige_xp(user_data: dict, xp_gain: int) -> tuple:
    """
    Adds prestige XP, applies rank-ups, and returns:
    (updated_user_data, ranked_up: bool, rank_up_message: str or None)
    """
    if is_weekend_boost_active():
        xp_gain *= 2

    points = user_data.get("prestige_points", 0)
    old_rank = get_prestige_rank(points)

    new_total = points + xp_gain
    new_rank = get_prestige_rank(new_total)

    user_data["prestige_points"] = new_total
    user_data["prestige"] = new_rank

    ranked_up = new_rank > old_rank
    message = None

    if ranked_up:
        class_info = get_prestige_class(user_data)
        if class_info:
            message = f"🎉 **Prestige Rank Up!** You are now Prestige {new_rank} — {class_info['title']}!"
        else:
            message = f"🎉 **Prestige Rank Up!** You are now Prestige {new_rank}!"

    return user_data, ranked_up, message
