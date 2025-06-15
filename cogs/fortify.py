# cogs/fortify.py — WARLAB stash fortification system + Visual UI Buttons (Fixed UI Crash)

import discord
from discord.ext import commands
from discord import app_commands
import json
from urllib.parse import quote
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
FORTIFY_UI_URL = "https://madv313.github.io/Stash-Fortify-UI/?data="

MAX_REINFORCEMENTS = {
    "Barbed Fence": 10,
    "Locked Container": 5,
    "Reinforced Gate": 5,
    "Claymore Trap": 1,
    "Guard Dog": 1
}

REINFORCEMENT_COSTS = {
    "Barbed Fence": {"tools": ["Pliers", "Nails"], "stash_hp": 1},
    "Locked Container": {"tools": ["Hammer", "Nails"], "stash_hp": 2},
    "Claymore Trap": {"tools": ["Pliers", "Nails"], "raid_block": 0.25},
    "Guard Dog": {"special": ["Guard Dog"], "raid_block": 0.5},
    "Reinforced Gate": {"tools": ["Hammer", "Saw", "Pliers", "Nails"], "stash_hp": 3}
}

class ReinforceButton(discord.ui.Button):
    def __init__(self, label):
        super().__init__(label=label, style=discord.ButtonStyle.blurple)
        self.rtype = label

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        profile = profiles.get(user_id)

        if not profile:
            await interaction.response.send_message("❌ Profile not found.", ephemeral=True)
            return

        rtype = self.rtype
        cost = REINFORCEMENT_COSTS[rtype]
        missing = []

        for tool in cost.get("tools", []):
            has_tool = any(t.startswith(tool) and "(0" not in t for t in profile.get("tools", []))
            if not has_tool:
                missing.append(tool)

        for item in cost.get("materials", []):
            if profile["inventory"].count(item) < 1:
                missing.append(item)

        for item in cost.get("special", []):
            if profile["inventory"].count(item) < 1:
                missing.append(item)

        if missing:
            await interaction.response.send_message(
                f"🔧 You’re missing: {', '.join(set(missing))}", ephemeral=True)
            return

        for item in cost.get("materials", []):
            profile["inventory"].remove(item)
        for item in cost.get("special", []):
            profile["inventory"].remove(item)

        for tool in cost.get("tools", []):
            for i, t in enumerate(profile["tools"]):
                if t.startswith(tool):
                    uses = int(t.split("(")[1].split()[0])
                    uses -= 1
                    if uses <= 0:
                        profile["tools"].pop(i)
                    else:
                        profile["tools"][i] = f"{tool} ({uses} uses left)"
                    break

        profile["reinforcements"][rtype] = profile["reinforcements"].get(rtype, 0) + 1
        if "stash_hp" in cost:
            profile["stash_hp"] += cost["stash_hp"]

        profiles[user_id] = profile
        await save_file(USER_DATA, profiles)

        preview_data = {
            "stash_hp": profile["stash_hp"],
            "reinforcements": profile["reinforcements"]
        }
        json_encoded = quote(json.dumps(preview_data))
        visual_link = f"{FORTIFY_UI_URL}{json_encoded}"

        embed = discord.Embed(
            title=f"✅ {rtype} installed!",
            description="Your stash has been fortified.",
            color=0x3498db
        )
        embed.add_field(name="Stash HP", value=str(profile["stash_hp"]), inline=True)
        embed.add_field(name="View Reinforcements", value=f"[Open Fortify UI]({visual_link})", inline=False)
        embed.set_footer(text="WARLAB | SV13 Bot")

        await interaction.response.send_message(embed=embed, ephemeral=True)

class ReinforcementView(discord.ui.View):
    def __init__(self, profile):
        super().__init__(timeout=90)
        for rtype in REINFORCEMENT_COSTS:
            current = profile["reinforcements"].get(rtype, 0)
            if current < MAX_REINFORCEMENTS[rtype]:
                self.add_item(ReinforceButton(label=rtype))

class Fortify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="fortify", description="Open fortification UI and choose reinforcement")
    async def fortify(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        profile = profiles.get(user_id, {
            "inventory": [],
            "tools": [],
            "reinforcements": {},
            "stash_hp": 0
        })
        profiles[user_id] = profile
        await save_file(USER_DATA, profiles)

        view = ReinforcementView(profile)

        if not view.children:
            await interaction.followup.send("✅ All stash reinforcements are fully installed. No more fortifications available.", ephemeral=True)
            return

        await interaction.followup.send("🔧 Select a reinforcement to install:", view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Fortify(bot))
