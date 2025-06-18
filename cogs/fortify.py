# cogs/fortify.py — WARLAB stash fortification system (flat stash logic + image generator)

import discord
from discord.ext import commands
from discord import app_commands
import json
from urllib.parse import quote
import os

from utils.fileIO import load_file, save_file
from stash_image_generator import generate_stash_image  # ✅ visual stash renderer

USER_DATA = "data/user_profiles.json"
CATALOG_PATH = "data/labskin_catalog.json"

MAX_REINFORCEMENTS = {
    "Barbed Fence": 9,
    "Locked Container": 5,
    "Reinforced Gate": 5,
    "Claymore Trap": 1,
    "Guard Dog": 1
}

REINFORCEMENT_COSTS = {
    "Barbed Fence": {"tools": ["Pliers", "Nails"], "stash_hp": 1},
    "Locked Container": {"tools": ["Hammer", "Nails"], "stash_hp": 2},
    "Claymore Trap": {"special": ["Claymore Trap"], "raid_block": 0.25},
    "Guard Dog": {"special": ["Guard Dog"], "raid_block": 0.5},
    "Reinforced Gate": {"tools": ["Hammer", "Saw", "Pliers", "Nails"], "stash_hp": 3}
}

TOOL_NAMES = ["Hammer", "Saw", "Nails", "Pliers"]
SPECIAL_NAMES = ["Guard Dog", "Claymore Trap"]

def render_stash_visual(reinforcements):
    bf = reinforcements.get("Barbed Fence", 0)
    lc = reinforcements.get("Locked Container", 0)
    rg = reinforcements.get("Reinforced Gate", 0)
    gd = reinforcements.get("Guard Dog", 0)
    cm = reinforcements.get("Claymore Trap", 0)

    lc_slots = ["🔐" if i < lc else "🔲" for i in range(5)]
    rg_row = " ".join(["🚪" if i < rg else "🔲" for i in range(5)])
    bf_emojis = ["🧱" if i < bf else "🔲" for i in range(9)]
    dog = "🐶" if gd else "🔲"
    clay = "💣" if cm else "🔲"

    row1 = f"{bf_emojis[0]} {bf_emojis[1]} {bf_emojis[2]} {bf_emojis[3]} {bf_emojis[4]}"
    row2 = f"{bf_emojis[5]} {lc_slots[0]} {lc_slots[1]} {lc_slots[2]} {bf_emojis[6]}"
    row3 = f"{bf_emojis[7]} {lc_slots[3]} 📦 {lc_slots[4]} {bf_emojis[8]}"
    row4 = rg_row
    row5 = f"  {dog}       {clay}"

    return f"{row1}\n{row2}\n{row3}\n{row4}\n{row5}"

def get_skin_visuals(profile, catalog):
    skin = profile.get("activeSkin", "default")
    skin_data = catalog.get(skin, {})
    return {
        "emoji": skin_data.get("emoji", "🏚️"),
        "color": skin_data.get("color", 0x8e44ad)
    }

class ReinforceButton(discord.ui.Button):
    def __init__(self, rtype):
        super().__init__(label=rtype, style=discord.ButtonStyle.blurple)
        self.rtype = rtype

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        profile = profiles.get(user_id)
        catalog = await load_file(CATALOG_PATH) or {}

        if not profile:
            await interaction.followup.send("❌ Profile not found.", ephemeral=True)
            return

        stash = profile.get("stash", [])
        reinforcements = profile.setdefault("reinforcements", {})
        profile.setdefault("stash_hp", 0)

        cost = REINFORCEMENT_COSTS[self.rtype]
        missing = []

        for tool in cost.get("tools", []):
            if stash.count(tool) < 1:
                missing.append(tool)
        for item in cost.get("special", []):
            if stash.count(item) < 1:
                missing.append(item)

        if missing:
            await interaction.followup.send(f"🔧 You’re missing: {', '.join(set(missing))}", ephemeral=True)
            return

        for tool in cost.get("tools", []):
            stash.remove(tool)
        for item in cost.get("special", []):
            stash.remove(item)

        reinforcements[self.rtype] = reinforcements.get(self.rtype, 0) + 1
        if "stash_hp" in cost:
            profile["stash_hp"] += cost["stash_hp"]

        profile["stash"] = stash
        profiles[user_id] = profile
        await save_file(USER_DATA, profiles)

        visuals = get_skin_visuals(profile, catalog)
        visual_text = render_stash_visual(reinforcements)

        remaining_tools = {t: stash.count(t) for t in TOOL_NAMES if t in stash}
        remaining_specials = {s: stash.count(s) for s in SPECIAL_NAMES if s in stash}

        tools_string = "\n".join(f"{tool} x{count}" for tool, count in remaining_tools.items()) or "None"
        specials_string = "\n".join(f"{item} x{count}" for item, count in remaining_specials.items()) or "None"

        try:
            stash_img_path = generate_stash_image(user_id, reinforcements, base_path="assets/stash_layers")
            file = discord.File(stash_img_path, filename="stash.png")

            embed = discord.Embed(
                title=f"{visuals['emoji']} Stash Layout",
                description=f"```
{visual_text}
```",
                color=visuals['color']
            )
            embed.add_field(name="✅ Installed", value=self.rtype, inline=False)
            embed.add_field(name="Stash HP", value=str(profile["stash_hp"]), inline=True)
            embed.add_field(name="Tools Remaining", value=tools_string, inline=False)
            embed.add_field(name="Specials Remaining", value=specials_string, inline=False)
            embed.set_image(url="attachment://stash.png")
            embed.set_footer(text="WARLAB | SV13 Bot")

            await self.view.main_msg.edit(embed=embed, attachments=[file], view=self.view)

        except Exception as e:
            print(f"❌ Error generating stash image: {e}")
            await self.view.main_msg.edit(content="⚠️ Reinforcement saved, but image failed to render.")

class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close", style=discord.ButtonStyle.danger, row=4)

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.view.main_msg.edit(content="❌ Fortification UI closed.", embed=None, view=None)
        except Exception as e:
            print(f"❌ Failed to close fortify UI: {e}")
        await interaction.response.defer()

class ReinforcementView(discord.ui.View):
    def __init__(self, profile):
        super().__init__(timeout=90)
        self.main_msg = None
        for rtype in REINFORCEMENT_COSTS:
            current = profile.get("reinforcements", {}).get(rtype, 0)
            if current < MAX_REINFORCEMENTS.get(rtype, 0):
                self.add_item(ReinforceButton(rtype))
        self.add_item(CloseButton())

class Fortify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="fortify", description="Open fortification UI and choose reinforcement")
    async def fortify(self, interaction: discord.Interaction):
        print(f"📥 /fortify triggered by {interaction.user} ({interaction.user.id})")
        await interaction.response.defer(ephemeral=True)

        try:
            user_id = str(interaction.user.id)
            profiles = await load_file(USER_DATA) or {}
            profile = profiles.get(user_id)
            catalog = await load_file(CATALOG_PATH) or {}

            if profile is None:
                await interaction.followup.send("❌ You don’t have a profile yet. Please use `/register` first.", ephemeral=True)
                return

            profile.setdefault("stash", [])
            profile.setdefault("reinforcements", {})
            profile.setdefault("stash_hp", 0)
            profiles[user_id] = profile
            await save_file(USER_DATA, profiles)

            visuals = get_skin_visuals(profile, catalog)
            visual_text = render_stash_visual(profile["reinforcements"])

            stash_img_path = generate_stash_image(user_id, profile["reinforcements"], base_path="assets/stash_layers")
            file = discord.File(stash_img_path, filename="stash.png")

            embed = discord.Embed(
                title=f"{visuals['emoji']} Stash Layout",
                description=f"```
{visual_text}
```",
                color=visuals['color']
            )
            embed.set_image(url="attachment://stash.png")
            embed.set_footer(text="Visual representation of your fortified stash.")

            view = ReinforcementView(profile)
            msg = await interaction.followup.send(embed=embed, file=file, view=view, ephemeral=True)
            view.main_msg = msg

        except Exception as e:
            print(f"❌ /fortify crashed: {e}")
            await interaction.followup.send("❌ Something went wrong while opening the fortification menu.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Fortify(bot))
