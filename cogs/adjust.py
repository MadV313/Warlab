# cogs/adjust.py — Fixed: Syncs with prestigeUtils, no hardcoded XP breakage

from utils.prestigeUtils import (
    get_prestige_rank,
    get_prestige_progress,
    apply_prestige_xp,
    broadcast_prestige_announcement
)

...

if action == "take":
    if current_rank <= 0:
        await interaction.response.send_message(f"⚠️ {user.mention} is already at **0 prestige**.", ephemeral=True)
        return
    if amount > current_rank:
        await interaction.response.send_message(
            f"❌ Cannot remove **{amount} prestige** — {user.mention} only has **{current_rank}**.",
            ephemeral=True)
        return

    # Calculate how much XP we need to subtract
    new_rank = current_rank - amount
    new_points = PRESTIGE_TIERS.get(new_rank, 0)

    profile["prestige_points"] = new_points
    profile["prestige"] = get_prestige_rank(new_points)
    result = f"🗑 Removed **{amount} prestige** from {user.mention}."
    print(f"✅ [Adjust] {result}")

elif action == "give":
    new_rank = current_rank + amount
    new_points = PRESTIGE_TIERS.get(new_rank, 0)

    # Apply XP via standard logic so it returns the proper DM format + allows rank-up messages
    xp_gain = new_points - current_points
    profile, ranked_up, msg, old_rank, new_rank = apply_prestige_xp(profile, xp_gain)

    result = f"✅ Gave **{amount} prestige** to {user.mention}."
    print(f"✅ [Adjust] {result}")

    if ranked_up:
        await broadcast_prestige_announcement(interaction.client, user, profile)

# Save and confirm
profiles[user_id] = profile
await save_file(USER_DATA, profiles)

rank_title = RANK_TITLES.get(profile["prestige"], "Prestige Specialist")
await interaction.response.send_message(
    f"{result}\n🏆 New Prestige Rank: **{profile['prestige']}** — *{rank_title}*",
    ephemeral=True
)
