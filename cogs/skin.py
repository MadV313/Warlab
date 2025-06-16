# cogs/skin.py — Admin: Give or remove Lab Skins using dynamic catalog

import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
CATALOG_PATH = "data/labskins_catalog.json"

class LabSkinManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_available_skins(self):
        catalog = await load_file(CATALOG_PATH) or {}
        return list(catalog.keys())

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="skin",
        description="Admin: Give or remove lab skins from a player."
    )
    @app_commands.describe(
        action="Give or remove a lab skin",
        user="Target player",
        skin="Name of the lab skin"
    )
    async def skin(
        self,
        interaction: discord.Interaction,
        action: Literal["give", "remove"],
        user: discord.Member,
        skin: str
    ):
        available_skins = await self.get_available_skins()

        if skin not in available_skins:
            await interaction.response.send_message(
                f"❌ Invalid skin. Choose from: {', '.join(available_skins)}",
                ephemeral=True
            )
            return

        profiles = await load_file(USER_DATA) or {}
        uid = str(user.id)
        profile = profiles.get(uid, {"labskins": []})
        owned_skins = profile.get("labskins", [])

        if action == "give":
            if skin not in owned_skins:
                owned_skins.append(skin)
            await interaction.response.send_message(
                f"✅ Skin **{skin}** unlocked for {user.mention}.",
                ephemeral=True
            )

        elif action == "remove":
            if skin in owned_skins:
                owned_skins.remove(skin)
                await interaction.response.send_message(
                    f"🗑 Skin **{skin}** removed from {user.mention}.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"⚠️ {user.mention} does not have that skin.",
                    ephemeral=True
                )
                return

        profile["labskins"] = owned_skins
        profiles[uid] = profile
        await save_file(USER_DATA, profiles)

    @skin.autocomplete("skin")
    async def autocomplete_skin(self, interaction: discord.Interaction, current: str):
        skins = await self.get_available_skins()
        return [
            app_commands.Choice(name=skin, value=skin)
            for skin in skins if current.lower() in skin.lower()
        ][:25]

async def setup(bot):
    await bot.add_cog(LabSkinManager(bot))
