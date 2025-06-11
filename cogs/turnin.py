# cogs/turnin.py — Submit crafted items for rewards

import discord
from discord.ext import commands
from discord import app_commands
from utils.fileIO import load_file, save_file
import json
from datetime import datetime

USER_DATA = "data/user_profiles.json"
TURNIN_LOG = "logs/turnin_log.json"

REWARD_VALUES = {
    "base_prestige": 50,
    "tactical_bonus": 100,
    "coin_enabled": True,
    "coin_bonus": 25  # Optional: reward both prestige and coins
}

class TurnIn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="turnin", description="Submit a crafted item for rewards")
    @app_commands.describe(item="Exact name of the crafted item or 'all' to submit everything")
    async def turnin(self, interaction: discord.Interaction, item: str):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        logs = await load_file(TURNIN_LOG) or {}

        user_data = profiles.get(user_id, {
            "username": interaction.user.name,
            "coins": 0,
            "prestige": 0,
            "tools": [],
            "parts": {},
            "blueprints": [],
            "crafted": [],
            "lastScavenge": None
        })

        crafted_items = user_data.get("crafted", [])
        if not crafted_items:
            await interaction.followup.send("❌ You have no crafted items to turn in.", ephemeral=True)
            return

        is_bulk = item.lower() == "all"
        items_to_turnin = crafted_items[:] if is_bulk else [item.strip()]

        reward_summary = []
        total_prestige = 0
        total_coins = 0

        for item_name in items_to_turnin:
            if item_name not in user_data["crafted"]:
                continue  # Skip non-existent or already turned-in items

            # Reward logic
            prestige = REWARD_VALUES["base_prestige"]
            if "Tactical" in item_name:
                prestige += REWARD_VALUES["tactical_bonus"]

            coins = REWARD_VALUES["coin_bonus"] if REWARD_VALUES["coin_enabled"] else 0
            total_prestige += prestige
            total_coins += coins

            # Remove from crafted
            user_data["crafted"].remove(item_name)

            # Log entry
            logs.setdefault(user_id, []).append({
                "item": item_name,
                "reward_prestige": prestige,
                "reward_coins": coins,
                "timestamp": datetime.utcnow().isoformat()
            })

            reward_summary.append(f"• **{item_name}** → 🧬 {prestige} Prestige" + (f" + 💰 {coins} Coins" if coins else ""))

        if not reward_summary:
            await interaction.followup.send("❌ No valid crafted items were found to turn in.", ephemeral=True)
            return

        user_data["prestige"] += total_prestige
        user_data["coins"] += total_coins
        profiles[user_id] = user_data

        await save_file(USER_DATA, profiles)
        await save_file(TURNIN_LOG, logs)

        embed = discord.Embed(
            title="📦 Items Turned In",
            description="\n".join(reward_summary),
            color=0x00ff00
        )
        embed.set_footer(text=f"Total: {total_prestige} Prestige" + (f", {total_coins} Coins" if total_coins else ""))
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(TurnIn(bot))
