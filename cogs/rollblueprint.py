# cogs/rollblueprint.py

import discord
from discord.ext import commands
from discord import app_commands
import random

from utils.fileIO import load_file, save_file
from utils.inventory import weighted_choice

USER_DATA = "data/user_profiles.json"
RARITY_WEIGHTS = "data/rarity_weights.json"

# Pool paths
WEAPON_PATH    = "data/item_recipes.json"
ARMOR_PATH     = "data/armor_blueprints.json"
EXPLOSIVE_PATH = "data/explosive_blueprints.json"

class RollBlueprint(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rollblueprint", description="Roll for a new random blueprint (1 per prestige)")
    async def rollblueprint(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)

        # Load files
        rarity_weights  = await load_file(RARITY_WEIGHTS)
        weapon_pool     = await load_file(WEAPON_PATH)
        armor_pool      = await load_file(ARMOR_PATH)
        explosive_pool  = await load_file(EXPLOSIVE_PATH)
        user_data       = await load_file(USER_DATA)

        if user_id not in user_data:
            await interaction.followup.send("❌ You don’t have a profile yet. Please use `/register` first.", ephemeral=True)
            return

        profile  = user_data[user_id]
        prestige = profile.get("prestige", 0)

        if prestige < 1:
            await interaction.followup.send("🔒 You must reach Prestige 1 to roll for blueprints.", ephemeral=True)
            return

        used_rolls = profile.get("blueprint_rolls_used", [])
        if prestige in used_rolls:
            await interaction.followup.send(f"⚠️ You've already used your blueprint roll for Prestige {prestige}.", ephemeral=True)
            return

        current_blueprints = profile.get("blueprints", [])

        # Build list of blueprints the player doesn't already have
        all_items = []
        for pool in (weapon_pool, armor_pool, explosive_pool):
            for key, entry in pool.items():
                produced = entry.get("produces")
                blueprint_name = f"{produced} Blueprint"
                if produced and blueprint_name not in current_blueprints:
                    all_items.append({
                        "item": blueprint_name,
                        "source_key": key,
                        "rarity": entry.get("rarity", "Common")
                    })

        if not all_items:
            await interaction.followup.send("✅ You’ve already unlocked all available blueprints!", ephemeral=True)
            return

        max_attempts = 10
        selected = None
        for _ in range(max_attempts):
            candidate = weighted_choice(all_items, rarity_weights)
            if candidate and candidate["item"] not in current_blueprints:
                selected = candidate
                break

        if not selected:
            await interaction.followup.send("❌ Failed to roll a unique blueprint. Please try again later.", ephemeral=True)
            return

        # Update user profile
        profile.setdefault("blueprints", []).append(selected["item"])
        profile.setdefault("blueprint_rolls_used", []).append(prestige)
        user_data[user_id] = profile
        await save_file(USER_DATA, user_data)

        await interaction.followup.send(
            f"📜 **New Blueprint Unlocked:** `{selected['item']}` (Rarity: {selected['rarity']})",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(RollBlueprint(bot))
