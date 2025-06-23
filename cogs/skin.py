# cogs/skin.py — Admin: Give or remove Lab Skins using dynamic catalog + Registration Check

import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
CATALOG_PATH = "data/labskin_catalog.json"

# ✅ Default fallback skin catalog if file missing or corrupted
FALLBACK_CATALOG = {
    "Rust Bucket": {
        "filename": "base_house_prestige1.png",
        "emoji": "🏚️", "color": 0x8e44ad
    },
    "Field Technician": {
        "filename": "base_house_prestige2.png",
        "emoji": "🏪", "color": 0x3498db
    },
    "Contaminated Worksite": {
        "filename": "base_house_prestige3.png",
        "emoji": "🏥", "color": 0xf1c40f
    },
    "Tactical Emerald": {
        "filename": "base_house_prestige4.png",
        "emoji": "🏢", "color": 0x2ecc71
    },
    "Warlab Blacksite": {
        "filename": "base_house_prestige5.png",
        "emoji": "🕋", "color": 0x111111
    },
    "Dark Ops": {
        "filename": "base_house_raid_master.png",
        "emoji": "🏰", "color": 0x2c3e50
    },
    "Architect's Vault": {
        "filename": "base_house_blueprint_master.png",
        "emoji": "🏛️", "color": 0xffffff
    },
    "Scavenger's Haven": {
        "filename": "base_house_scavenge_master.png",
        "emoji": "🛖", "color": 0xd35400
    }
}

class LabSkinManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_available_skins(self):
        catalog = await load_file(CATALOG_PATH)
        return list((catalog or FALLBACK_CATALOG).keys())

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

        if uid not in profiles:
            await interaction.response.send_message(
                f"❌ That player does not have a profile yet. Ask them to use `/register` first.",
                ephemeral=True
            )
            return

        profile = profiles[uid]
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
