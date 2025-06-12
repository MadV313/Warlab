# cogs/labskins.py — Equip unlocked lab skins (Prestige IV required)

import discord
from discord.ext import commands
from discord import app_commands
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"

class LabSkinSelect(discord.ui.Select):
    def __init__(self, user_id, available_skins):
        self.user_id = user_id
        options = [
            discord.SelectOption(label=skin, value=skin)
            for skin in available_skins
        ]
        super().__init__(placeholder="Choose your Lab Skin", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("⛔ Only the original user can select their lab skin.", ephemeral=True)
            return

        profiles = await load_file(USER_DATA) or {}
        profile = profiles.get(self.user_id, {})
        profile["activeSkin"] = self.values[0]
        profiles[self.user_id] = profile
        await save_file(USER_DATA, profiles)

        await interaction.response.send_message(f"🎨 Lab skin set to **{self.values[0]}**.", ephemeral=True)

class LabSkinView(discord.ui.View):
    def __init__(self, user_id, skins):
        super().__init__(timeout=60)
        self.add_item(LabSkinSelect(user_id, skins))

class LabSkins(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="labskins", description="Equip a visual theme for your lab (Prestige 4 required)")
    async def labskins(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        profile = profiles.get(user_id, {
            "labskins": [],
            "activeSkin": "default",
            "prestige": 0
        })

        if profile.get("prestige", 0) < 4:
            await interaction.followup.send("🔒 Prestige IV required to use lab skins.", ephemeral=True)
            return

        unlocked_skins = profile.get("labskins", [])
        if not unlocked_skins:
            await interaction.followup.send("⚠️ You have not unlocked any lab skins yet.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎨 Choose Your Lab Skin",
            description="Select a visual theme to customize your lab.",
            color=0x3498db
        )
        embed.set_footer(text=f"Current skin: {profile.get('activeSkin', 'default')}")

        view = LabSkinView(user_id, unlocked_skins)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(LabSkins(bot))
