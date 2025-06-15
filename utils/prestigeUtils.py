# utils/prestigeUtils.py — Centralized Prestige Rank System

PRESTIGE_TIERS = {
    1: 200,     # Prestige I
    2: 500,     # Prestige II
    3: 1000,    # Prestige III
    4: 2000,    # Prestige IV (Lab Skins Unlock)
    5: 3000     # Prestige V (Special Unlocks)
}

def get_prestige_rank(points: int) -> int:
    """
    Returns the player's current Prestige rank based on total prestige points.
    """
    for rank in sorted(PRESTIGE_TIERS.keys(), reverse=True):
        if points >= PRESTIGE_TIERS[rank]:
            return rank
    return 0

def get_prestige_progress(points: int) -> dict:
    """
    Returns a dictionary showing current prestige rank and how many points needed for next.
    """
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
