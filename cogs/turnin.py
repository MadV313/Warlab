# cogs/turnin.py — Submit crafted items for rewards

import discord
from discord.ext import commands
from discord import app_commands
from utils.fileIO import load_file, save_file
import json

USER_DATA = "data/user_profiles.json"
TURNIN_LOG = "logs/turnin_log.json"

REWARD_VALUES = {
    "base": 50,
    "tactical_bonus": 100
}

class TurnIn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="turnin", description="Submit a crafted item for rewards")
    @app_commands.describe(item="Exact name of the crafted item in your inventory")
    async def turnin(self, interaction: discord.Interaction, item: str):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        logs = await load_file(TURNIN_LOG) or {}

        user_data = profiles.get(user_id, {"inventory": [], "prestige": 0})
        item_name = item.strip()

        if item_name not in user_data["inventory"]:
            await interaction.followup.send("❌ You don't have that item in your inventory.", ephemeral=True)
            return

        # Remove and reward
        user_data["inventory"].remove(item_name)
        base_reward = REWARD_VALUES["base"]
        bonus = REWARD_VALUES["tactical_bonus"] if "Full Tactical Build" in item_name else 0
        coins_earned = base_reward + bonus
        user_data["prestige"] += coins_earned  # You could swap this for a wallet system

        # Log it
        logs.setdefault(user_id, []).append({
            "item": item_name,
            "reward": coins_earned,
            "timestamp": interaction.created_at.isoformat()
        })

        profiles[user_id] = user_data
        await save_file(USER_DATA, profiles)
        await save_file(TURNIN_LOG, logs)

        await interaction.followup.send(f"📦 You turned in **{item_name}** and earned **{coins_earned} Prestige Points**!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TurnIn(bot))

