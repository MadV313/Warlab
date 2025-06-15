# cogs/fortify.py — WARLAB stash fortification system + Visual UI Preview (no type input)

import discord
from discord.ext import commands
from discord import app_commands
import json
from urllib.parse import quote

from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
FORTIFY_UI_URL = "https://madv313.github.io/Stash-Fortify-UI/?data="  # ✅ Hosted UI endpoint

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

class Fortify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="fortify", description="Open your stash fortification UI")
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

        # 🔍 Prepare Visual UI link
        preview_data = {
            "stash_hp": profile["stash_hp"],
            "reinforcements": profile["reinforcements"]
        }
        json_encoded = quote(json.dumps(preview_data))
        visual_link = f"{FORTIFY_UI_URL}{json_encoded}"

        # ✅ Final embed with open UI button
        embed = discord.Embed(
            title="🛡️ Fortify Your Stash",
            description="Visualize and reinforce your stash below.",
            color=0x3498db
        )
        embed.add_field(name="Stash HP", value=str(profile["stash_hp"]), inline=True)
        embed.add_field(name="View Reinforcements", value=f"[Open Fortify UI]({visual_link})", inline=False)
        embed.set_footer(text="WARLAB | SV13 Bot")

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Fortify(bot))
