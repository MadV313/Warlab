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

# Pool paths
WEAPON_PATH = "data/item_recipes.json"
ARMOR_PATH = "data/armor_blueprints.json"
EXPLOSIVE_PATH = "data/explosive_blueprints.json"

class RollBlueprint(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rollblueprint", description="Roll for a random blueprint based on rarity")
    async def rollblueprint(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)

        # Load data
        rarity_weights = await load_file(RARITY_WEIGHTS)
        weapon_pool = await load_file(WEAPON_PATH)
        armor_pool = await load_file(ARMOR_PATH)
        explosive_pool = await load_file(EXPLOSIVE_PATH)
        unlocked = await load_file(UNLOCKED_BLUEPRINTS) or {}

        all_items = []

        for source in (weapon_pool, armor_pool, explosive_pool):
            for key, entry in source.items():
                all_items.append({
                    "item": entry["produces"],
                    "source_key": key,
                    "rarity": entry.get("rarity", "Common")
                })

        # Select item using rarity weighting
        selected_item = weighted_choice(all_items, rarity_weights)

        if not selected_item:
            await interaction.followup.send("❌ Failed to roll a blueprint. Please try again.", ephemeral=True)
            return

        # Track unlock
        user_unlocked = unlocked.get(user_id, [])
        if selected_item not in user_unlocked:
            user_unlocked.append(selected_item)
            unlocked[user_id] = user_unlocked
            await save_file(UNLOCKED_BLUEPRINTS, unlocked)
            msg = f"📜 You unlocked a new blueprint: **{selected_item}**!"
        else:
            msg = f"📜 You rolled: **{selected_item}** (already unlocked)"

        await interaction.followup.send(msg, ephemeral=True)

async def setup(bot):
    await bot.add_cog(RollBlueprint(bot))
