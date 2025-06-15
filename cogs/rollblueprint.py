# cogs/rollblueprint.py

import discord
from discord.ext import commands
from discord import app_commands
import random

from utils.fileIO import load_file, save_file
from utils.inventory import weighted_choice

USER_DATA = "data/user_profiles.json"
RARITY_WEIGHTS = "data/rarity_weights.json"
UNLOCKED_BLUEPRINTS = "data/unlocked_blueprints.json"
PRESTIGE_USAGE_TRACKER = "data/blueprint_roll_tracker.json"

# Pool paths
WEAPON_PATH = "data/item_recipes.json"
ARMOR_PATH = "data/armor_blueprints.json"
EXPLOSIVE_PATH = "data/explosive_blueprints.json"

class RollBlueprint(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rollblueprint", description="Roll for a new random blueprint (1 per prestige)")
    async def rollblueprint(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)

        # Load files
        rarity_weights = await load_file(RARITY_WEIGHTS)
        weapon_pool = await load_file(WEAPON_PATH)
        armor_pool = await load_file(ARMOR_PATH)
        explosive_pool = await load_file(EXPLOSIVE_PATH)
        unlocked = await load_file(UNLOCKED_BLUEPRINTS) or {}
        user_data = await load_file(USER_DATA)
        roll_tracker = await load_file(PRESTIGE_USAGE_TRACKER) or {}

        prestige = user_data.get(user_id, {}).get("prestige", 0)
        if prestige < 1:
            await interaction.followup.send("❌ You must reach Prestige 1 to roll for blueprints.", ephemeral=True)
            return

        # Check if user already rolled at this prestige
        used_levels = roll_tracker.get(user_id, [])
        if prestige in used_levels:
            await interaction.followup.send(f"⚠️ You've already used your blueprint roll for Prestige {prestige}.", ephemeral=True)
            return

        # Build the full list of available blueprints
        all_items = []
        unlocked_items = unlocked.get(user_id, [])

        for source in (weapon_pool, armor_pool, explosive_pool):
            for key, entry in source.items():
                produced = entry["produces"]
                if produced not in unlocked_items:
                    all_items.append({
                        "item": produced,
                        "source_key": key,
                        "rarity": entry.get("rarity", "Common")
                    })

        if not all_items:
            await interaction.followup.send("✅ You’ve already unlocked all available blueprints!", ephemeral=True)
            return

        # Roll a blueprint using rarity weighting
        selected = weighted_choice(all_items, rarity_weights)
        if not selected:
            await interaction.followup.send("❌ Failed to roll a blueprint. Please try again later.", ephemeral=True)
            return

        # Update unlock and usage tracking
        unlocked.setdefault(user_id, []).append(selected["item"])
        roll_tracker.setdefault(user_id, []).append(prestige)

        await save_file(UNLOCKED_BLUEPRINTS, unlocked)
        await save_file(PRESTIGE_USAGE_TRACKER, roll_tracker)

        await interaction.followup.send(
            f"📜 **New Blueprint Unlocked:** `{selected['item']}` (Rarity: {selected['rarity']})",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(RollBlueprint(bot))
