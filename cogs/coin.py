# cogs/coin.py — Admin: Give or take coins from a player (clean, simple version)

import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"

class CoinManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="coin", description="Admin: Give or take coins from a player")
    @app_commands.describe(
        action="Give or take coins",
        user="Player to modify",
        amount="Amount of coins to give or take"
    )
    async def coin(
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
        profile = profiles.get(user_id, {"coins": 0})
        current_coins = profile.get("coins", 0)

        if action == "take":
            if current_coins <= 0:
                await interaction.response.send_message(f"⚠️ {user.mention} already has **0 coins**.", ephemeral=True)
                return
            if amount > current_coins:
                await interaction.response.send_message(f"❌ Cannot remove **{amount} coins** — {user.mention} only has **{current_coins} coins**.", ephemeral=True)
                return
            profile["coins"] = current_coins - amount
            result = f"🗑 Removed **{amount} coins** from {user.mention}."

        elif action == "give":
            profile["coins"] = current_coins + amount
            result = f"✅ Gave **{amount} coins** to {user.mention}."

        profiles[user_id] = profile
        await save_file(USER_DATA, profiles)

        await interaction.response.send_message(f"{result}\n💰 New Balance: **{profile['coins']} coins**", ephemeral=True)

async def setup(bot):
    await bot.add_cog(CoinManager(bot))
