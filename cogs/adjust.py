# cogs/adjust.py — Admin: Adjust prestige rank (give/take levels) [Persistent + Debug Ready]

import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from datetime import datetime

from utils.fileIO import load_file, save_file
from utils.prestigeUtils import broadcast_prestige_announcement  # ✅ WARLAB rank-up alerts

USER_DATA = "data/user_profiles.json"
WARLAB_CHANNEL_ID = 1382187883590455296  # Warlab broadcast target

RANK_TITLES = {
    0: "Unranked Survivor",
    1: "Field Engineer",
    2: "Weapon Tech",
    3: "Shadow Engineer",
    4: "Warlab Veteran",
    5: "Legendary Craftsman",
    6: "Legend",
    7: "Apex",
    8: "Ghost",
    9: "Mythic",
    10: "Master Chief"
}

SPECIAL_REWARDS = {
    1: {"title": "💉 Weaponsmith Elite", "color": 0x3cb4fc},
    2: {"title": "🔬 Scavenger Elite",    "color": 0x88e0a0},
    3: {"title": "☣️ Raider Elite",       "color": 0x880808}
}

class AdjustPrestige(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="adjust", description="Admin: Give or take prestige ranks from a player")
    @app_commands.describe(
        action="Give or take prestige ranks",
        user="Player to adjust",
        amount="Number of prestige ranks to adjust by"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def adjust(
        self,
        interaction: discord.Interaction,
        action: Literal["give", "take"],
        user: discord.Member,
        amount: int
    ):
        if amount <= 0:
            await interaction.response.send_message("⚠️ Amount must be greater than 0.", ephemeral=True)
            return

        user_id = str(user.id)
        print(f"📡 [Adjust] Loading profiles from {USER_DATA}")
        profiles = await load_file(USER_DATA) or {}

        if user_id not in profiles:
            print(f"❌ [Adjust] Profile not found for UID {user_id}")
            await interaction.response.send_message(
                f"❌ That player does not have a profile yet. Ask them to use `/register` first.",
                ephemeral=True
            )
            return

        profile = profiles[user_id]
        current_prestige = profile.get("prestige", 0)

        if action == "take":
            if current_prestige <= 0:
                print(f"⚠️ [Adjust] {user.display_name} already at 0 prestige.")
                await interaction.response.send_message(
                    f"⚠️ {user.mention} is already at **0 prestige**.", ephemeral=True)
                return
            if amount > current_prestige:
                print(f"❌ [Adjust] Cannot remove {amount} from {current_prestige}")
                await interaction.response.send_message(
                    f"❌ Cannot remove **{amount} prestige** — {user.mention} only has **{current_prestige}**.",
                    ephemeral=True)
                return
            profile["prestige"] = current_prestige - amount
            result = f"🗑 Removed **{amount} prestige** from {user.mention}."
            print(f"✅ [Adjust] {result}")

        elif action == "give":
            profile["prestige"] = current_prestige + amount
            result = f"✅ Gave **{amount} prestige** to {user.mention}."
            print(f"✅ [Adjust] {result}")
            await broadcast_prestige_announcement(interaction.client, user, profile)

        profiles[user_id] = profile
        print(f"📤 [Adjust] Saving profile for UID {user_id}")
        await save_file(USER_DATA, profiles)

        rank_title = RANK_TITLES.get(profile["prestige"], "Prestige Specialist")
        await interaction.response.send_message(
            f"{result}\n🏆 New Prestige Rank: **{profile['prestige']}** — *{rank_title}*",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(AdjustPrestige(bot))
