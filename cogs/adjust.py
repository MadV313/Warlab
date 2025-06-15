# cogs/adjust.py — Admin: Adjust prestige rank (give/take levels)

import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"

class AdjustPrestige(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="adjust", description="Admin: Give or take prestige ranks from a player")
    @app_commands.describe(
        action="Give or take prestige ranks",
        user="Player to adjust",
        amount="Number of prestige ranks to adjust by"
    )
    async def adjust(
        self,
        interaction: discord.Interaction,
        action: Literal["give", "take"],
        user: discord.Member,
        amount: int
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You don’t have permission to use this.", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("⚠️ Amount must be greater than 0.", ephemeral=True)
            return

        user_id = str(user.id)
        profiles = await load_file(USER_DATA) or {}
        profile = profiles.get(user_id, {"prestige": 0})
        current_prestige = profile.get("prestige", 0)

        if action == "take":
            if current_prestige <= 0:
                await interaction.response.send_message(f"⚠️ {user.mention} is already at **0 prestige**.", ephemeral=True)
                return
            if amount > current_prestige:
                await interaction.response.send_message(f"❌ Cannot remove **{amount} prestige** — {user.mention} only has **{current_prestige}**.", ephemeral=True)
                return
            profile["prestige"] = current_prestige - amount
            result = f"🗑 Removed **{amount} prestige** from {user.mention}."

        elif action == "give":
            profile["prestige"] = current_prestige + amount
            result = f"✅ Gave **{amount} prestige** to {user.mention}."

        profiles[user_id] = profile
        await save_file(USER_DATA, profiles)

        await interaction.response.send_message(f"{result}\n🏆 New Prestige Rank: **{profile['prestige']}**", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdjustPrestige(bot))
