# cogs/fortify.py — WARLAB stash fortification system + Visual UI Buttons (Live Refresh + Close + Disable Maxed Buttons)

import discord
from discord.ext import commands
from discord import app_commands
import json
from urllib.parse import quote
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
FORTIFY_UI_URL = "https://madv313.github.io/Stash-Fortify-UI/?data="

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
    "Claymore Trap": {"tools": ["Pliers", "Nails"], "raid_block": 0.25},
    "Guard Dog": {"special": ["Guard Dog"], "raid_block": 0.5},
    "Reinforced Gate": {"tools": ["Hammer", "Saw", "Pliers", "Nails"], "stash_hp": 3}
}

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

class ReinforceButton(discord.ui.Button):
    def __init__(self, rtype):
        super().__init__(label=rtype, style=discord.ButtonStyle.blurple)
        self.rtype = rtype

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        profile = profiles.get(user_id)

        if not profile:
            await interaction.response.send_message("❌ Profile not found.", ephemeral=True)
            return

        cost = REINFORCEMENT_COSTS[self.rtype]
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
            await interaction.response.send_message(f"🔧 You’re missing: {', '.join(set(missing))}", ephemeral=True)
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

        profile["reinforcements"][self.rtype] = profile["reinforcements"].get(self.rtype, 0) + 1
        if "stash_hp" in cost:
            profile["stash_hp"] += cost["stash_hp"]

        profiles[user_id] = profile
        await save_file(USER_DATA, profiles)

        # 🔄 Live update the visual embed
        visual_embed = discord.Embed(
            title="🏚️ Stash Layout",
            description=f"```\n{render_stash_visual(profile['reinforcements'])}\n```",
            color=0x8e44ad
        )
        visual_embed.set_footer(text="Visual representation of your fortified stash.")
        await self.view.stored_messages[0].edit(embed=visual_embed)

        # 🔁 Refresh the buttons to disable any maxed-out options
        new_view = ReinforcementView(profile)
        new_view.stored_messages = self.view.stored_messages
        await self.view.stored_messages[1].edit(view=new_view)

        # ✅ Feedback embed
        preview_data = {
            "stash_hp": profile["stash_hp"],
            "reinforcements": profile["reinforcements"],
            "tools": profile["tools"]
        }
        json_encoded = quote(json.dumps(preview_data))
        visual_link = f"{FORTIFY_UI_URL}{json_encoded}"

        confirm = discord.Embed(
            title=f"✅ {self.rtype} installed!",
            description="Your stash has been fortified.",
            color=0x3498db
        )
        confirm.add_field(name="Stash HP", value=str(profile["stash_hp"]), inline=True)
        confirm.add_field(name="Tools Remaining", value="\n".join(profile["tools"]) or "None", inline=False)
        confirm.add_field(name="View Reinforcements", value=f"[Open Fortify UI]({visual_link})", inline=False)
        confirm.set_footer(text="WARLAB | SV13 Bot")
        await interaction.response.send_message(embed=confirm, ephemeral=True)

class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close", style=discord.ButtonStyle.danger, row=4)

    async def callback(self, interaction: discord.Interaction):
        try:
            for msg in getattr(self.view, "stored_messages", []):
                await msg.delete()
        except Exception as e:
            print(f"❌ Failed to delete ephemeral messages: {e}")
        await interaction.response.defer()

class ReinforcementView(discord.ui.View):
    def __init__(self, profile):
        super().__init__(timeout=90)
        self.stored_messages = []
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

            if profile is None:
                await interaction.followup.send("❌ You must use `/register` before accessing your stash.", ephemeral=True)
                return

            profile.setdefault("inventory", [])
            profile.setdefault("tools", [])
            profile.setdefault("reinforcements", {})
            profile.setdefault("stash_hp", 0)

            profiles[user_id] = profile
            await save_file(USER_DATA, profiles)

            visual_text = render_stash_visual(profile["reinforcements"])
            visual_embed = discord.Embed(
                title="🏚️ Stash Layout",
                description=f"```\n{visual_text}\n```",
                color=0x8e44ad
            )
            visual_embed.set_footer(text="Visual representation of your fortified stash.")
            visual_msg = await interaction.followup.send(embed=visual_embed, ephemeral=True)

            view = ReinforcementView(profile)
            button_msg = await interaction.followup.send("🔧 Select a reinforcement to install:", view=view, ephemeral=True)
            view.stored_messages = [visual_msg, button_msg]

        except Exception as e:
            print(f"❌ /fortify crashed: {e}")
            await interaction.followup.send("❌ Something went wrong while opening the fortification menu.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Fortify(bot))
