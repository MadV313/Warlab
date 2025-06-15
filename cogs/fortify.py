# cogs/fortify.py — WARLAB stash fortification system + Damage Tracking + Tool Durability Display

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

        # Update tools and reduce durability
        updated_tools = []
        for tool in profile["tools"]:
            base = tool.split(" (")[0]
            if base in cost.get("tools", []) and "(0" not in tool:
                uses = int(tool.split("(")[1].split()[0])
                uses -= 1
                if uses > 0:
                    updated_tools.append(f"{base} ({uses} uses left)")
                # If uses drop to 0, do not re-add
                cost["tools"].remove(base)  # avoid double use
            else:
                updated_tools.append(tool)
        profile["tools"] = updated_tools

        # Initialize or update reinforcement
        reinf = profile.get("reinforcements", {})
        if rtype not in reinf or isinstance(reinf[rtype], int):
            reinf[rtype] = {"count": 1, "damage": 0}
        else:
            reinf[rtype]["count"] += 1
        profile["reinforcements"] = reinf

        if "stash_hp" in cost:
            profile["stash_hp"] += cost["stash_hp"]

        profiles[user_id] = profile
        await save_file(USER_DATA, profiles)

        preview_data = {
            "stash_hp": profile["stash_hp"],
            "reinforcements": reinf
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

        if profile["tools"]:
            embed.add_field(name="🧰 Tools Remaining", value="\n".join(profile["tools"]), inline=False)

        embed.set_footer(text="WARLAB | SV13 Bot")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ReinforcementView(discord.ui.View):
    def __init__(self, profile):
        super().__init__(timeout=90)
        for rtype in REINFORCEMENT_COSTS:
            current_data = profile["reinforcements"].get(rtype, {})
            current = current_data["count"] if isinstance(current_data, dict) else current_data
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
    
        # Upgrade old reinforcements
        for k, v in profile.get("reinforcements", {}).items():
            if isinstance(v, int):
                profile["reinforcements"][k] = {"count": v, "damage": 0}
    
        profiles[user_id] = profile
        await save_file(USER_DATA, profiles)
    
        view = ReinforcementView(profile)
    
        if not view.children:
            await interaction.followup.send(
                content="✅ All stash reinforcements are fully installed. No more fortifications available.",
                ephemeral=True
            )
            return
    
        # FINAL SAFE UI SEND (no embed, safe with all clients):
        await interaction.followup.send(
            content="🔧 Select a reinforcement to install:",
            view=view,
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Fortify(bot))
