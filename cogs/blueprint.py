# cogs/blueprint.py — Admin: Give or remove blueprint unlocks (dynamic dropdowns)

import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
RECIPE_FILES = [
    "data/item_recipes.json",
    "data/armor_blueprints.json",
    "data/explosive_blueprints.json"
]

class BlueprintManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_all_blueprints(self):
        blueprints = set()
        for path in RECIPE_FILES:
            data = await load_file(path) or {}
            for entry in data.values():
                produced = entry.get("produces")
                if produced:
                    blueprints.add(f"{produced} Blueprint")
        return sorted(blueprints)

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="blueprint",
        description="Admin: Give or remove blueprints from a player"
    )
    @app_commands.describe(
        action="Give or remove blueprint",
        user="Target player",
        item="Blueprint name from game data",
        quantity="Quantity to give (ignored when removing)"
    )
    async def blueprint(
        self,
        interaction: discord.Interaction,
        action: Literal["give", "remove"],
        user: discord.Member,
        item: str,
        quantity: int
    ):
        if quantity <= 0 and action == "give":
            await interaction.response.send_message("⚠️ Quantity must be greater than 0.", ephemeral=True)
            return

        item = item.strip()
        valid_blueprints = await self.get_all_blueprints()
        if item not in valid_blueprints:
            await interaction.response.send_message(
                f"❌ Invalid blueprint.\nChoose from: {', '.join(valid_blueprints)}",
                ephemeral=True
            )
            return

        profiles = await load_file(USER_DATA) or {}
        user_id = str(user.id)
        profile = profiles.get(user_id, {"inventory": [], "blueprints": []})
        blueprints = profile.get("blueprints", [])

        if action == "give":
            if item not in blueprints:
                blueprints.append(item)
            await interaction.response.send_message(
                f"✅ Blueprint **{item}** unlocked for {user.mention}.",
                ephemeral=True
            )

        elif action == "remove":
            if item in blueprints:
                blueprints.remove(item)
                await interaction.response.send_message(
                    f"🗑 Blueprint **{item}** removed from {user.mention}.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"⚠️ {user.mention} does not have that blueprint.",
                    ephemeral=True
                )
                return

        profile["blueprints"] = blueprints
        profiles[user_id] = profile
        await save_file(USER_DATA, profiles)

    @blueprint.autocomplete("item")
    async def autocomplete_item(self, interaction: discord.Interaction, current: str):
        all_items = await self.get_all_blueprints()
        return [
            app_commands.Choice(name=bp, value=bp)
            for bp in all_items if current.lower() in bp.lower()
        ][:25]

async def setup(bot):
    await bot.add_cog(BlueprintManager(bot))
