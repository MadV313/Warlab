# cogs/adjust.py — Admin: Adjust prestige rank (give/take levels) [Synced with prestigeUtils]

import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal

from utils.fileIO import load_file, save_file
from utils.prestigeUtils import (
    PRESTIGE_TIERS,
    get_prestige_rank,
    apply_prestige_xp,
    broadcast_prestige_announcement
)

USER_DATA = "data/user_profiles.json"
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

class AdjustPrestige(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="adjust", description="Admin: Give or take prestige ranks from a player")
    @app_commands.describe(
        action="Give or take prestige ranks",
        user="Player to adjust",
        amount="Number of prestige ranks to adjust by"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def adjust(
        self,
        interaction: discord.Interaction,
        action: Literal["give", "take"],
        user: discord.Member,
        amount: int
    ):
        if amount <= 0:
            await interaction.response.send_message("⚠️ Amount must be greater than 0.", ephemeral=True)
            return

        user_id = str(user.id)
        profiles = await load_file(USER_DATA) or {}

        if user_id not in profiles:
            await interaction.response.send_message(
                "❌ That player does not have a profile yet. Ask them to use `/register` first.",
                ephemeral=True
            )
            return

        profile = profiles[user_id]
        current_points = profile.get("prestige_points", 0)
        current_rank = get_prestige_rank(current_points)

        if action == "take":
            if current_rank <= 0:
                await interaction.response.send_message(
                    f"⚠️ {user.mention} is already at **0 prestige**.", ephemeral=True)
                return
            if amount > current_rank:
                await interaction.response.send_message(
                    f"❌ Cannot remove **{amount} prestige** — {user.mention} only has **{current_rank}**.",
                    ephemeral=True)
                return

            new_rank = current_rank - amount
            new_points = PRESTIGE_TIERS.get(new_rank, 0)

            profile["prestige_points"] = new_points
            profile["prestige"] = get_prestige_rank(new_points)

            result = f"🗑 Removed **{amount} prestige** from {user.mention}."

        elif action == "give":
            new_rank = current_rank + amount
            new_points = PRESTIGE_TIERS.get(new_rank, 0)

            xp_gain = new_points - current_points
            profile, ranked_up, msg, old_rank, new_rank = apply_prestige_xp(profile, xp_gain)

            if ranked_up:
                await broadcast_prestige_announcement(interaction.client, user, profile)

            result = f"✅ Gave **{amount} prestige** to {user.mention}."

        # Save update
        profiles[user_id] = profile
        await save_file(USER_DATA, profiles)

        rank_title = RANK_TITLES.get(profile["prestige"], "Prestige Specialist")
        await interaction.response.send_message(
            f"{result}\n🏆 New Prestige Rank: **{profile['prestige']}** — *{rank_title}*",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(AdjustPrestige(bot))
