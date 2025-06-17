# cogs/blueprint.py — Admin: Give or remove blueprint unlocks (with clean storage)

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
                    blueprints.add(produced)  # 🔑 Store clean key only
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
        await interaction.response.defer(ephemeral=True)

        if quantity <= 0 and action == "give":
            await interaction.followup.send("⚠️ Quantity must be greater than 0.", ephemeral=True)
            return

        item = item.replace(" Blueprint", "").strip()  # 🧼 Strip suffix
        valid_blueprints = await self.get_all_blueprints()
        if item not in valid_blueprints:
            await interaction.followup.send(
                f"❌ Invalid blueprint.\nChoose from: {', '.join(bp + ' Blueprint' for bp in valid_blueprints)}",
                ephemeral=True
            )
            return

        profiles = await load_file(USER_DATA) or {}
        user_id = str(user.id)
        profile = profiles.get(user_id, {"inventory": [], "blueprints": []})
        blueprints = profile.get("blueprints", [])

        if action == "give":
            added = False
            for _ in range(quantity):
                if item not in blueprints:
                    blueprints.append(item)
                    added = True
            if added:
                await interaction.followup.send(
                    f"✅ Blueprint **{item}** unlocked for {user.mention}.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"⚠️ {user.mention} already has blueprint **{item}**.",
                    ephemeral=True
                )

        elif action == "remove":
            if item in blueprints:
                blueprints.remove(item)
                await interaction.followup.send(
                    f"🗑 Blueprint **{item}** removed from {user.mention}.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
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
            app_commands.Choice(name=bp + " Blueprint", value=bp + " Blueprint")
            for bp in all_items if current.lower() in bp.lower()
        ][:25]

async def setup(bot):
    await bot.add_cog(BlueprintManager(bot))
