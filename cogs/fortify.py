# cogs/fortify.py — WARLAB stash fortification system + UI Preview

import discord
from discord.ext import commands
from discord import app_commands
import json
from urllib.parse import quote

from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
FORTIFY_UI_URL = "https://madv313.github.io/Stash-Fortify-UI/?data="  # 🔁 Your hosted fortify UI endpoint

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
    "Guard Dog": {"tools": [], "special": ["Guard Dog"], "raid_block": 0.5},
    "Reinforced Gate": {"tools": ["Hammer", "Saw", "Pliers", "Nails"], "stash_hp": 3}
}

class Fortify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="fortify", description="Reinforce your stash with tools and materials")
    @app_commands.describe(type="Choose a reinforcement to install")
    async def fortify(self, interaction: discord.Interaction, type: str):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        profile = profiles.get(user_id, {
            "inventory": [],
            "tools": [],
            "reinforcements": {},
            "stash_hp": 0
        })

        type = type.title()
        if type not in REINFORCEMENT_COSTS:
            await interaction.followup.send("❌ Invalid reinforcement type.", ephemeral=True)
            return

        # Check limit
        current_count = profile["reinforcements"].get(type, 0)
        max_allowed = MAX_REINFORCEMENTS[type]
        if current_count >= max_allowed:
            await interaction.followup.send(f"⚠️ You’ve already reached the max of {max_allowed} {type}s.", ephemeral=True)
            return

        cost = REINFORCEMENT_COSTS[type]
        missing = []

        # Check materials
        for item in cost["materials"]:
            if profile["inventory"].count(item) < 1:
                missing.append(item)

        # Check tools (validates durability)
        for tool in cost["tools"]:
            has_tool = any(t.startswith(tool) and "(0" not in t for t in profile.get("tools", []))
            if not has_tool:
                missing.append(tool)

        if missing:
            await interaction.followup.send(f"🔧 You’re missing: {', '.join(set(missing))}", ephemeral=True)
            return

        # Deduct materials
        for item in cost["materials"]:
            profile["inventory"].remove(item)

        # Reduce tool durability
        for tool in cost["tools"]:
            for i, t in enumerate(profile["tools"]):
                if t.startswith(tool):
                    uses = int(t.split("(")[1].split()[0])
                    uses -= 1
                    if uses <= 0:
                        profile["tools"].pop(i)
                    else:
                        profile["tools"][i] = f"{tool} ({uses} uses left)"
                    break

        # Apply upgrade
        profile["reinforcements"][type] = current_count + 1
        if "stash_hp" in cost:
            profile["stash_hp"] += cost["stash_hp"]

        profiles[user_id] = profile
        await save_file(USER_DATA, profiles)

        # 🔍 Prepare visual preview link
        preview_data = {
            "stash_hp": profile["stash_hp"],
            "reinforcements": profile["reinforcements"]
        }
        json_encoded = quote(json.dumps(preview_data))
        visual_link = f"{FORTIFY_UI_URL}{json_encoded}"

        # ✅ Final response with UI
        embed = discord.Embed(
            title=f"✅ {type} installed!",
            description=f"Your stash has been fortified.",
            color=0x3498db
        )
        embed.add_field(name="Stash HP", value=str(profile["stash_hp"]), inline=True)
        embed.add_field(name="View Reinforcements", value=f"[Open Fortify UI]({visual_link})", inline=False)
        embed.set_footer(text="WARLAB | SV13 Bot")

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Fortify(bot))
