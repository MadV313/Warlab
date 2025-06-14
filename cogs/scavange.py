# cogs/scavenge.py — WARLAB daily gathering logic (with rarity weighting + weekend bonus)

import discord
from discord.ext import commands
from discord import app_commands
import json
import random
from datetime import datetime, timedelta

from utils.fileIO import load_file, save_file
from utils.inventory import weighted_choice

USER_DATA = "data/user_profiles.json"
RARITY_WEIGHTS = "data/rarity_weights.json"

# === Rarity-tagged Loot Pool ===
SCAVENGE_LOOT = [
    {"item": "Nails", "rarity": "Common"},
    {"item": "Wood Plank", "rarity": "Common"},
    {"item": "Scrap Metal", "rarity": "Uncommon"},
    {"item": "Duct Tape", "rarity": "Uncommon"},
    {"item": "Screwdriver", "rarity": "Rare"},
    {"item": "Wrench", "rarity": "Rare"},
    {"item": "Suppressor", "rarity": "Legendary"}
]

class Scavenge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="scavenge", description="Scavenge for random materials (1x per day)")
    async def scavenge(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)
        now = datetime.utcnow()

        profiles = await load_file(USER_DATA) or {}

        # Abort if user has no profile
        if user_id not in profiles:
            await interaction.followup.send("❌ You don’t have a profile yet. Use `/register` to get started.", ephemeral=True)
            return

        user = profiles[user_id]
        last_time_str = user.get("last_scavenge")
        cooldown_min = interaction.client.config.get("scavenge_cooldown_minutes", 1440)

        # Cooldown check
        if last_time_str:
            last_time = datetime.fromisoformat(last_time_str)
            if now < last_time + timedelta(minutes=cooldown_min):
                remaining = (last_time + timedelta(minutes=cooldown_min)) - now
                mins = int(remaining.total_seconds() // 60)
                await interaction.followup.send(f"⏳ You must wait **{mins} more minutes** before scavenging again.", ephemeral=True)
                return

        # Load rarity weights
        rarity_weights = await load_file(RARITY_WEIGHTS)
        if not rarity_weights:
            await interaction.followup.send("⚠️ Loot weights missing. Contact staff.", ephemeral=True)
            return

        # Rarity-weighted loot pulls (2 pulls + bonus on weekends)
        found = []
        for _ in range(2):
            item = weighted_choice(SCAVENGE_LOOT, rarity_weights)
            if item:
                found.append(item["item"])

        if now.weekday() in [5, 6]:  # Weekend bonus
            print("📣 Weekend event active — adding bonus item.")
            bonus = weighted_choice(SCAVENGE_LOOT, rarity_weights)
            if bonus:
                found.append(bonus["item"])

        # Update profile
        user.setdefault("inventory", [])
        user["inventory"].extend(found)
        user["last_scavenge"] = now.isoformat()
        profiles[user_id] = user
        await save_file(USER_DATA, profiles)

        # Log and feedback
        print(f"🟢 /scavenge by {interaction.user.display_name} — found {found}")
        if found:
            await interaction.followup.send(f"🔎 You scavenged and found: **{', '.join(found)}**", ephemeral=True)
        else:
            await interaction.followup.send("🔎 You searched but found nothing this time.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Scavenge(bot))
