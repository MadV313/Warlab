# utils/prestigeUtils.py — Centralized Prestige Rank System

PRESTIGE_TIERS = {
    1: 200,     # Prestige I
    2: 400,     # Prestige II
    3: 600,     # Prestige III
    4: 800,     # Prestige IV (Lab Skins Unlock)
    5: 1000     # Prestige V (Special Unlocks)
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

def apply_prestige_xp(user_data: dict, xp_gain: int) -> tuple:
    """
    Adds prestige XP and auto-applies rank ups. Returns (updated_user_data, ranked_up).
    """
    points = user_data.get("prestige_points", 0)
    old_rank = get_prestige_rank(points)

    new_total = points + xp_gain
    new_rank = get_prestige_rank(new_total)

    user_data["prestige_points"] = new_total
    user_data["prestige"] = new_rank

    return user_data, new_rank > old_rank
