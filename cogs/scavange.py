# cogs/scavenge.py — WARLAB daily gathering logic (with rarity weighting + debug)

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
        print(f"🟢 /scavenge triggered by {interaction.user.display_name} ({interaction.user.id})")
        await interaction.response.defer(ephemeral=True)

        try:
            user_id = str(interaction.user.id)
            now = datetime.utcnow()

            profiles = await load_file(USER_DATA) or {}
            user = profiles.get(user_id, {"inventory": [], "last_scavenge": None})

            # ✅ FIX: Access config from bot instance
            cooldown_min = getattr(self.bot, "config", {}).get("scavenge_cooldown_minutes", 1440)
            if user["last_scavenge"]:
                last_time = datetime.fromisoformat(user["last_scavenge"])
                if now < last_time + timedelta(minutes=cooldown_min):
                    remaining = (last_time + timedelta(minutes=cooldown_min)) - now
                    mins = int(remaining.total_seconds() // 60)
                    print(f"⏳ Cooldown active: {mins} mins remaining")
                    await interaction.followup.send(f"⏳ You must wait {mins} more minutes before scavenging again.", ephemeral=True)
                    return

            rarity_weights = await load_file(RARITY_WEIGHTS)
            print(f"📊 Rarity weights loaded: {rarity_weights}")

            found = []

            # Main pulls
            for i in range(2):
                item = weighted_choice(SCAVENGE_LOOT, rarity_weights)
                if isinstance(item, dict):
                    item_name = item.get("item")
                else:
                    item_name = item
                print(f"🎯 Pull {i+1}: {item_name}")
                if item_name:
                    found.append(item_name)

            # Weekend bonus
            if now.weekday() in [5, 6]:
                print("🎉 Weekend bonus roll triggered")
                bonus = weighted_choice(SCAVENGE_LOOT, rarity_weights)
                bonus_name = bonus.get("item") if isinstance(bonus, dict) else bonus
                print(f"🎁 Bonus: {bonus_name}")
                if bonus_name:
                    found.append(bonus_name)

            # Update profile
            user["inventory"].extend(found)
            user["last_scavenge"] = now.isoformat()
            profiles[user_id] = user
            await save_file(USER_DATA, profiles)

            if found:
                print(f"📦 Items found: {found}")
                await interaction.followup.send(f"🔎 You scavenged and found: **{', '.join(found)}**", ephemeral=True)
            else:
                print("📭 Nothing found")
                await interaction.followup.send("🔎 You searched but found nothing this time.", ephemeral=True)

        except Exception as e:
            print(f"❌ SCAVENGE EXCEPTION: {e}")
            await interaction.followup.send("⚠️ Something went wrong during scavenging.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Scavenge(bot))
