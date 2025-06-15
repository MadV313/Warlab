# cogs/labskins.py — Lab skin equip command with unlock validation

import discord
from discord.ext import commands
from discord import app_commands
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
CATALOG_PATH = "data/labskin_catalog.json"

class LabSkinSelect(discord.ui.Select):
    def __init__(self, user_id, available_skins, catalog, profile):
        self.user_id = user_id
        self.profile = profile
        self.catalog = catalog

        options = []
        for skin in available_skins:
            data = catalog.get(skin, {})
            emoji = data.get("emoji", None)
            description = data.get("description", "No description.")
            options.append(
                discord.SelectOption(
                    label=skin,
                    value=skin,
                    description=description[:100],
                    emoji=emoji
                )
            )

        super().__init__(placeholder="Choose your Lab Skin", min_values=1, max_values=1, options=options)

    def meets_unlock_conditions(self, skin: str) -> bool:
        requirements = self.catalog.get(skin, {}).get("unlock", {})
        prestige_needed = requirements.get("prestige", 0)
        builds_required = requirements.get("builds_required", 0)
        raids_required = requirements.get("raids_successful", 0)

        return (
            self.profile.get("prestige", 0) >= prestige_needed and
            self.profile.get("lab_builds", 0) >= builds_required and
            self.profile.get("raids_successful", 0) >= raids_required
        )

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("⛔ Only you can select your lab skin.", ephemeral=True)
            return

        selected = self.values[0]
        if not self.meets_unlock_conditions(selected):
            await interaction.response.send_message("🔒 You haven't unlocked that skin yet.", ephemeral=True)
            return

        profiles = await load_file(USER_DATA) or {}
        profile = profiles.get(self.user_id, {})
        profile["activeSkin"] = selected
        profiles[self.user_id] = profile
        await save_file(USER_DATA, profiles)

        await interaction.response.send_message(f"✅ Lab skin set to **{selected}**.", ephemeral=True)

class LabSkinView(discord.ui.View):
    def __init__(self, user_id, skins, catalog, profile):
        super().__init__(timeout=60)
        self.add_item(LabSkinSelect(user_id, skins, catalog, profile))

class LabSkins(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="labskins", description="Equip a visual theme for your lab (Prestige IV required)")
    async def labskins(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        profile = profiles.get(user_id, {
            "prestige": 0,
            "lab_builds": 0,
            "raids_successful": 0,
            "labskins": [],
            "activeSkin": "default"
        })

        if profile.get("prestige", 0) < 1:
            await interaction.followup.send("🔒 Prestige I required to use lab skins.", ephemeral=True)
            return

        unlocked_skins = profile.get("labskins", [])
        if not unlocked_skins:
            await interaction.followup.send("⚠️ You have not unlocked any lab skins yet.", ephemeral=True)
            return

        catalog = await load_file(CATALOG_PATH) or {}
        active_skin = profile.get("activeSkin", "default")
        active_skin_info = catalog.get(active_skin, {})

        embed = discord.Embed(
            title="🎨 Choose Your Lab Skin",
            description="Select a visual theme to customize your lab.",
            color=active_skin_info.get("color", 0x3498db)
        )
        embed.set_footer(text=f"Current skin: {active_skin}")

        view = LabSkinView(user_id, unlocked_skins, catalog, profile)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(LabSkins(bot))
