# cogs/craft.py — WARLAB /craft logic

import discord
from discord.ext import commands
from discord import app_commands
import json

from utils.fileIO import load_file, save_file
from utils.inventory import has_required_parts, remove_parts
from utils.prestigeBonusHandler import can_craft_tactical, can_craft_explosives

USER_DATA = "data/user_profiles.json"
RECIPE_DATA = "data/item_recipes.json"

class Craft(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="craft", description="Craft a weapon or item from available parts")
    @app_commands.describe(item="Name of the item to craft")
    async def craft(self, interaction: discord.Interaction, item: str):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        recipes = await load_file(RECIPE_DATA) or {}

        item_lower = item.lower()
        if item_lower not in recipes:
            await interaction.followup.send("❌ Unknown item. Please check the blueprint name.", ephemeral=True)
            return

        recipe = recipes[item_lower]
        user_data = profiles.get(user_id, {
            "inventory": [],
            "blueprints": [],
            "prestige": 0,
            "tools": [],
            "parts": {},
            "crafted": [],
            "labskins": [],
            "activeSkin": "default",
            "lastScavenge": None
        })

        prestige = user_data.get("prestige", 0)

        # === Prestige-gated crafting checks ===
        if "tactical" in item_lower and not can_craft_tactical(prestige):
            await interaction.followup.send("🔒 You must be Prestige II to craft tactical gear.", ephemeral=True)
            return

        if "explosive" in item_lower and not can_craft_explosives(prestige):
            await interaction.followup.send("🔒 You must be Prestige III to craft explosives or special items.", ephemeral=True)
            return

        # === Check parts
        if not has_required_parts(user_data["inventory"], recipe["requirements"]):
            reqs = ", ".join([f"{v}x {k}" for k, v in recipe["requirements"].items()])
            await interaction.followup.send(f"❌ You’re missing parts. Needed: {reqs}", ephemeral=True)
            return

        # === Craft it
        remove_parts(user_data["inventory"], recipe["requirements"])
        user_data["inventory"].append(recipe["produces"])
        profiles[user_id] = user_data
        await save_file(USER_DATA, profiles)

        await interaction.followup.send(f"✅ Crafted **{recipe['produces']}** successfully!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Craft(bot))
