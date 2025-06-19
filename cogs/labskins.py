# cogs/labskins.py — Lab skin equip command with unlock validation and hardcoded descriptions

import discord
from discord.ext import commands
from discord import app_commands
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
CATALOG_PATH = "data/labskin_catalog.json"

# 🧱 Mapping of lab skin names to base image paths
SKIN_IMAGE_PATHS = {
    "Rust Bucket": "assets/stash_layers/base_house_prestige1.PNG",
    "Field Technician": "assets/stash_layers/base_house_prestige2.png",
    "Contaminated Worksite": "assets/stash_layers/base_house_prestige3.png",
    "Tactical Emerald": "assets/stash_layers/base_house_prestige4.png",
    "Warlab Blacksite": "assets/stash_layers/base_house_prestige5.png",
    "Dark Ops": "assets/stash_layers/base_house_raid_master.png",
    "Architect's Vault": "assets/stash_layers/base_house_blueprint_master.png",
    "Scavenger's Haven": "assets/stash_layers/base_house_scavenge_master.png"
}

# 📝 Hardcoded descriptions for dropdown clarity
SKIN_DESCRIPTIONS = {
    "Rust Bucket": "Corroded, rusty old lab setup. Basic, no frills.",
    "Field Technician": "Tactical repair station used by survivors in the field.",
    "Contaminated Worksite": "Bright yellow, with biohazard symbols. High-security zone.",
    "Tactical Emerald": "Sleek green tactical theme. Everything is more advanced here.",
    "Warlab Blacksite": "Secret blacksite aesthetics. Shadowy, elite. Prestige-exclusive.",
    "Dark Ops": "Impenetrable fortress awarded only to Raid Masters.",
    "Architect's Vault": "Pristine high-tech lab awarded only to Blueprint Masters.",
    "Scavenger's Haven": "Makeshift but well-organized survivor lab awarded only to Scavenge Masters."
}

class LabSkinSelect(discord.ui.Select):
    def __init__(self, user_id, available_skins, catalog, profile):
        self.user_id = user_id
        self.profile = profile
        self.catalog = catalog
        self.unlocked = profile.get("labskins", [])

        options = []
        for skin in available_skins:
            data = catalog.get(skin, {})
            emoji = data.get("emoji", None)
            description = SKIN_DESCRIPTIONS.get(skin, "No description.")
            options.append(
                discord.SelectOption(
                    label=skin,
                    value=skin,
                    description=description[:100],
                    emoji=emoji
                )
            )

        super().__init__(
            placeholder="Choose your Lab Skin",
            min_values=1,
            max_values=1,
            options=options,
            disabled=False
        )

    def meets_unlock_conditions(self, skin: str) -> bool:
        if skin in self.unlocked:
            return True

        prestige = self.profile.get("prestige", 0)
        raids = self.profile.get("raids_successful", 0)
        scavenges = self.profile.get("scavenges_completed", 0)
        blueprints = self.profile.get("blueprints_unlocked", [])

        return (
            (skin == "Rust Bucket" and prestige >= 1) or
            (skin == "Field Technician" and prestige >= 2) or
            (skin == "Contaminated Worksite" and prestige >= 3) or
            (skin == "Tactical Emerald" and prestige >= 4) or
            (skin == "Warlab Blacksite" and prestige >= 5) or
            (skin == "Dark Ops" and raids >= 25) or
            (skin == "Architect's Vault" and blueprints == "all") or
            (skin == "Scavenger's Haven" and scavenges >= 100)
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
        profile["baseImage"] = SKIN_IMAGE_PATHS.get(selected, "assets/stash_layers/base_house_prestige1.PNG")

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

    @app_commands.command(name="labskins", description="Equip a visual theme for your lab (Prestige I required)")
    async def labskins(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        profile = profiles.get(user_id)

        if not profile:
            await interaction.followup.send("❌ You don’t have a profile yet. Please use `/register` first.", ephemeral=True)
            return

        if profile.get("prestige", 0) < 1:
            await interaction.followup.send("🔒 Prestige I required to use lab skins.", ephemeral=True)
            return

        catalog = await load_file(CATALOG_PATH) or {}
        unlocked_skins = []

        prestige = profile.get("prestige", 0)
        raids = profile.get("raids_successful", 0)
        scavenges = profile.get("scavenges_completed", 0)
        blueprints = profile.get("blueprints_unlocked", [])

        if prestige >= 1:
            unlocked_skins.append("Rust Bucket")
        if prestige >= 2:
            unlocked_skins.append("Field Technician")
        if prestige >= 3:
            unlocked_skins.append("Contaminated Worksite")
        if prestige >= 4:
            unlocked_skins.append("Tactical Emerald")
        if prestige >= 5:
            unlocked_skins.append("Warlab Blacksite")
        if raids >= 25:
            unlocked_skins.append("Dark Ops")
        if blueprints == "all":
            unlocked_skins.append("Architect's Vault")
        if scavenges >= 100:
            unlocked_skins.append("Scavenger's Haven")

        unlocked_skins += [s for s in profile.get("labskins", []) if s not in unlocked_skins]

        if not unlocked_skins:
            await interaction.followup.send("⚠️ You have not unlocked any lab skins yet.", ephemeral=True)
            return

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
