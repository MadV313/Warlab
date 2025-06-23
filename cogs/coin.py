# cogs/coin.py — Admin: Give or take coins from a player (persistent + debug logging + floor = -100)

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
        print(f"📥 [CoinManager] Loading profiles for coin update: {user_id}")
        profiles = await load_file(USER_DATA) or {}

        if user_id not in profiles:
            print(f"❌ [CoinManager] No profile found for {user_id}")
            await interaction.response.send_message(
                f"❌ That player does not have a profile yet. Ask them to use `/register` first.",
                ephemeral=True
            )
            return

        profile = profiles[user_id]
        current_coins = profile.get("coins", 0)
        print(f"💰 [CoinManager] Current coins: {current_coins}")

        if action == "take":
            new_total = current_coins - amount
            if new_total < -100:
                await interaction.response.send_message(
                    f"❌ Cannot reduce coins below **-100**.\nCurrent: **{current_coins}**, Requested: **-{amount}**",
                    ephemeral=True
                )
                return
            profile["coins"] = new_total
            result = f"🗑 Removed **{amount} coins** from {user.mention}."
            print(f"🧾 [CoinManager] Removed {amount} coins from UID: {user_id}, New Total: {new_total}")

        elif action == "give":
            profile["coins"] = current_coins + amount
            result = f"✅ Gave **{amount} coins** to {user.mention}."
            print(f"🧾 [CoinManager] Gave {amount} coins to UID: {user_id}, New Total: {profile['coins']}")

        profiles[user_id] = profile
        print(f"📤 [CoinManager] Saving profile update for UID: {user_id}")
        await save_file(USER_DATA, profiles)

        await interaction.response.send_message(
            f"{result}\n💰 New Balance: **{profile['coins']} coins**",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(CoinManager(bot))
