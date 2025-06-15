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
