# cogs/scavenge.py — WARLAB daily gathering logic (with rarity weighting)

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
        user = profiles.get(user_id, {"inventory": [], "last_scavenge": None})

        # Check cooldown
        cooldown_min = interaction.client.config.get("scavenge_cooldown_minutes", 1440)
        if user["last_scavenge"]:
            last_time = datetime.fromisoformat(user["last_scavenge"])
            if now < last_time + timedelta(minutes=cooldown_min):
                remaining = (last_time + timedelta(minutes=cooldown_min)) - now
                mins = int(remaining.total_seconds() // 60)
                await interaction.followup.send(f"⏳ You must wait {mins} more minutes before scavenging again.", ephemeral=True)
                return

        # Load rarity weights
        rarity_weights = await load_file(RARITY_WEIGHTS)

        # Rarity-weighted loot pulls (2 attempts)
        found = []
        for _ in range(2):
            item = weighted_choice(SCAVENGE_LOOT, rarity_weights)
            if item:
                found.append(item["item"])

        # Weekend bonus
        is_weekend = now.weekday() in [5, 6]
        if is_weekend:
            print("📣 Weekend Event Active! Bonus rewards applied.")
            bonus_item = weighted_choice(SCAVENGE_LOOT, rarity_weights)
            if bonus_item:
                found.append(bonus_item["item"])

        # Update user data
        user["inventory"].extend(found)
        user["last_scavenge"] = now.isoformat()
        profiles[user_id] = user
        await save_file(USER_DATA, profiles)

        # Result message
        if found:
            await interaction.followup.send(f"🔎 You scavenged and found: **{', '.join(found)}**", ephemeral=True)
        else:
            await interaction.followup.send("🔎 You searched but found nothing this time.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Scavenge(bot))

class Scavenge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="scavenge", description="Scavenge for random materials (1x per day)")
    async def scavenge(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        now = datetime.utcnow()

        profiles = await load_file(USER_DATA) or {}
        user = profiles.get(user_id, {"inventory": [], "last_scavenge": None})

        # Check cooldown
        cooldown_min = interaction.client.config.get("scavenge_cooldown_minutes", 1440)
        if user["last_scavenge"]:
            last_time = datetime.fromisoformat(user["last_scavenge"])
            if now < last_time + timedelta(minutes=cooldown_min):
                remaining = (last_time + timedelta(minutes=cooldown_min)) - now
                mins = int(remaining.total_seconds() // 60)
                await interaction.followup.send(f"⏳ You must wait {mins} more minutes before scavenging again.", ephemeral=True)
                return

        # Scavenge roll
        found = []
        for loot in SCAVENGE_LOOT:
            if random.random() < loot["chance"]:
                found.append(loot["item"])

        # Update user data
        user["inventory"].extend(found)
        user["last_scavenge"] = now.isoformat()
        profiles[user_id] = user
        await save_file(USER_DATA, profiles)

        # Result message
        if found:
            await interaction.followup.send(f"🔎 You scavenged and found: **{', '.join(found)}**", ephemeral=True)
        else:
            await interaction.followup.send("🔎 You searched but found nothing this time.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Scavenge(bot))
