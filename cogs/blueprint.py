# cogs/blueprint.py — Admin: Give or remove blueprint unlocks (with remote storage + debug + validation)

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
        print("📦 [BlueprintManager] Fetching all blueprint names from recipe files...")
        blueprints = set()
        for path in RECIPE_FILES:
            data = await load_file(path) or {}
            for entry in data.values():
                produced = entry.get("produces")
                if produced:
                    blueprints.add(produced)
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

        item = item.replace(" Blueprint", "").strip()
        full_item = f"{item} Blueprint"

        print(f"📋 [BlueprintManager] Validating blueprint: {full_item}")
        valid_blueprints = await self.get_all_blueprints()
        if item not in valid_blueprints:
            await interaction.followup.send(
                f"❌ Invalid blueprint.\nChoose from: {', '.join(bp + ' Blueprint' for bp in valid_blueprints)}",
                ephemeral=True
            )
            return

        print(f"📡 [BlueprintManager] Loading user profiles from: {USER_DATA}")
        profiles = await load_file(USER_DATA) or {}
        user_id = str(user.id)

        if user_id not in profiles:
            await interaction.followup.send(
                f"❌ That player does not have a profile yet. Ask them to use `/register` first.",
                ephemeral=True
            )
            print(f"❌ [BlueprintManager] Profile not found for UID: {user_id}")
            return

        profile = profiles.get(user_id)
        blueprints = profile.get("blueprints", [])
        if not isinstance(blueprints, list):
            blueprints = []

        if action == "give":
            if full_item in blueprints:
                await interaction.followup.send(
                    f"⚠️ {user.mention} already has blueprint **{full_item}**.",
                    ephemeral=True
                )
                print(f"⚠️ [BlueprintManager] Duplicate blueprint not added for UID: {user_id}")
            else:
                blueprints.append(full_item)
                await interaction.followup.send(
                    f"✅ Blueprint **{full_item}** unlocked for {user.mention}.",
                    ephemeral=True
                )
                print(f"✅ [BlueprintManager] Added blueprint '{full_item}' to UID: {user_id}")

        elif action == "remove":
            if full_item not in blueprints:
                await interaction.followup.send(
                    f"⚠️ {user.mention} does not have blueprint **{full_item}**.",
                    ephemeral=True
                )
                print(f"⚠️ [BlueprintManager] Tried to remove non-existent blueprint for UID: {user_id}")
                return
            blueprints.remove(full_item)
            await interaction.followup.send(
                f"🗑 Blueprint **{full_item}** removed from {user.mention}.",
                ephemeral=True
            )
            print(f"🗑 [BlueprintManager] Removed blueprint '{full_item}' from UID: {user_id}")

        profile["blueprints"] = blueprints
        profiles[user_id] = profile

        print(f"📤 [BlueprintManager] Saving updated profile for UID: {user_id}")
        await save_file(USER_DATA, profiles)

    @blueprint.autocomplete("item")
    async def autocomplete_item(self, interaction: discord.Interaction, current: str):
        all_items = await self.get_all_blueprints()
        print(f"🔍 [BlueprintManager] Autocomplete lookup for: {current}")
        return [
            app_commands.Choice(name=bp + " Blueprint", value=bp + " Blueprint")
            for bp in all_items if current.lower() in bp.lower()
        ][:25]

async def setup(bot):
    await bot.add_cog(BlueprintManager(bot))
