# utils/prestigeUtils.py — Centralized Prestige Rank System (Remote-persistent ready)

from utils.boosts import is_weekend_boost_active
from utils.fileIO import load_file, save_file  # Ready for future persistence support
import discord
from datetime import datetime

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

RANK_TITLES = {
    0: "Unranked Survivor",
    1: "Field Engineer",
    2: "Weapon Tech",
    3: "Shadow Engineer",
    4: "Warlab Veteran",
    5: "Legendary Craftsman",
    6: "Legend",
    7: "Apex",
    8: "Ghost",
    9: "Mythic",
    10: "Master Chief"
}

WARLAB_CHANNEL_ID = 1382187883590455296

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

async def broadcast_prestige_announcement(bot: discord.Client, member: discord.Member, profile: dict):
    """
    Sends a prestige rank-up announcement to the WARLAB channel.
    """
    new_rank = profile.get("prestige", 0)
    rank_title = RANK_TITLES.get(new_rank, "Prestige Specialist")
    special_class = get_prestige_class(profile)

    emb = discord.Embed(
        title="🧬 Prestige Unlocked!",
        description=(
            f"{member.mention} reached **Prestige {new_rank}**\n"
            f"🎖 Rank Title: **{rank_title}**\n" +
            (f"📛 Prestige Class: **{special_class['title']}**\n" if special_class else "") +
            "\n🎲 Use /rollblueprint to try for a new schematic!"
        ),
        color=special_class["color"] if special_class else 0x6b8e23,
        timestamp=datetime.utcnow()
    )
    emb.set_thumbnail(url=member.display_avatar.url)

    channel = bot.get_channel(WARLAB_CHANNEL_ID)
    if channel:
        await channel.send(embed=emb)
