# cogs/labskins.py — Lab skin equip command with unlock validation and base image assignment

import discord
from discord.ext import commands
from discord import app_commands
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
CATALOG_PATH = "data/labskin_catalog.json"

# 🧱 Mapping of lab skin names to corresponding base image filenames
SKIN_IMAGE_PATHS = {
    "Rust Bucket": "assets/stash_layers/base_house_prestige1.PNG",
    "Field Technician": "assets/stash_layers/base_house_prestige2.png",
    "Contaminated Worksite": "assets/stash_layers/base_house_prestige3.png",
    "Tactical Emerald": "assets/stash_layers/house_base_prestige4.png",
    "Warlab Blacksite": "assets/stash_layers/base_house_prestige5.png",
    "Dark Ops": "assets/stash_layers/base_house_raid_master.png",
    "Architect's Vault": "assets/stash_layers/base_house_blueprint_master.png",
    "Scavenger's Haven": "assets/stash_layers/base_house_scavenge_master.png"
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
            description = data.get("description", "No description.")
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
            return True  # ✅ Player was granted the skin manually

        requirements = self.catalog.get(skin, {}).get("unlock", {})
        prestige_needed = requirements.get("prestige", 0)
        builds_required = requirements.get("builds_required", 0)
        raids_required = requirements.get("raids_successful", 0)
        scavenges_required = requirements.get("scavenges_completed", 0)
        blueprints_required = requirements.get("blueprints_unlocked", None)

        if blueprints_required == "all":
            if self.profile.get("blueprints_unlocked", []) != "all":
                return False

        return (
            self.profile.get("prestige", 0) >= prestige_needed and
            self.profile.get("lab_builds", 0) >= builds_required and
            self.profile.get("raids_successful", 0) >= raids_required and
            self.profile.get("scavenges_completed", 0) >= scavenges_required
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

        # ✅ Determine available skins (auto-include if player meets requirements)
        for skin, data in catalog.items():
            unlock = data.get("unlock", {})
            prestige_needed = unlock.get("prestige", 0)
            builds_required = unlock.get("builds_required", 0)
            raids_required = unlock.get("raids_successful", 0)
            scavenges_required = unlock.get("scavenges_completed", 0)
            blueprints_required = unlock.get("blueprints_unlocked", None)

            meets_blueprints = True
            if blueprints_required == "all":
                meets_blueprints = profile.get("blueprints_unlocked", []) == "all"

            if (
                profile.get("prestige", 0) >= prestige_needed and
                profile.get("lab_builds", 0) >= builds_required and
                profile.get("raids_successful", 0) >= raids_required and
                profile.get("scavenges_completed", 0) >= scavenges_required and
                meets_blueprints
            ):
                unlocked_skins.append(skin)

        # ✅ Add manually granted skins
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
