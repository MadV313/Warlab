# cogs/adjust.py — Admin: Adjust prestige rank (give/take levels)

import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from datetime import datetime
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
WARLAB_CHANNEL_ID = 1382187883590455296  # ✅ WARLAB broadcast channel

RANK_TITLES = {
    0: "Unranked Survivor",
    1: "Field Engineer",
    2: "Weapon Tech",
    3: "Shadow Engineer",
    4: "Warlab Veteran",
    5: "Legendary Craftsman"
}

SPECIAL_REWARDS = {
    1: {"title": "💉 Weaponsmith Elite", "color": 0x3cb4fc},
    2: {"title": "🔬 Scavenger Elite",    "color": 0x88e0a0},
    3: {"title": "☣️ Raider Elite",       "color": 0x880808}
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
        profile = profiles.get(user_id, {"prestige": 0})
        current_prestige = profile.get("prestige", 0)

        if action == "take":
            if current_prestige <= 0:
                await interaction.response.send_message(
                    f"⚠️ {user.mention} is already at **0 prestige**.", ephemeral=True)
                return
            if amount > current_prestige:
                await interaction.response.send_message(
                    f"❌ Cannot remove **{amount} prestige** — {user.mention} only has **{current_prestige}**.",
                    ephemeral=True)
                return
            profile["prestige"] = current_prestige - amount
            new_rank = profile["prestige"]
            result = f"🗑 Removed **{amount} prestige** from {user.mention}."

        elif action == "give":
            profile["prestige"] = current_prestige + amount
            new_rank = profile["prestige"]
            result = f"✅ Gave **{amount} prestige** to {user.mention}."

            # Send broadcast embed to WARLAB
            rolled_id = profile.get("special_class") or 1
            reward = SPECIAL_REWARDS.get(rolled_id, SPECIAL_REWARDS[1])
            rank_title = RANK_TITLES.get(new_rank, "Prestige Specialist")

            emb = discord.Embed(
                title="🧬 Prestige Unlocked!",
                description=(
                    f"{user.mention} reached **Prestige {new_rank}**\n"
                    f"🎖 Rank Title: **{rank_title}**\n"
                    f"📛 Prestige Class: **{reward['title']}**\n\n"
                    "🎲 Use /rollblueprint to try for a new schematic!"
                ),
                color=reward["color"],
                timestamp=datetime.utcnow()
            )
            emb.set_thumbnail(url=user.display_avatar.url)

            ch = interaction.client.get_channel(WARLAB_CHANNEL_ID)
            if ch:
                await ch.send(embed=emb)

        profiles[user_id] = profile
        await save_file(USER_DATA, profiles)

        rank_title = RANK_TITLES.get(profile["prestige"], "Prestige Specialist")
        await interaction.response.send_message(
            f"{result}\n🏆 New Prestige Rank: **{profile['prestige']}** — *{rank_title}*",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(AdjustPrestige(bot))
