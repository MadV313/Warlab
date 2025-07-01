import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
WARLAB_CHANNEL_ID = 1382187883590455296  # Warlab channel ID

class WarlabNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="warlabnuke", description="☢️ ADMIN: Reset all Warlab player data!")
    @app_commands.guilds(discord.Object(id=1166441420643639348))  # Your server ID
    @app_commands.checks.has_permissions(administrator=True)
    async def warlabnuke(self, interaction: discord.Interaction):
        print(f"☢️ [warlabnuke] Called by {interaction.user} ({interaction.user.id})")

        # Restrict to Warlab channel
        if interaction.channel_id != WARLAB_CHANNEL_ID:
            return await interaction.response.send_message(
                "❌ This command can only be used in the Warlab channel.", ephemeral=True
            )

        # Confirmation prompt
        await interaction.response.send_message(
            "⚠️ Are you **sure** you want to NUKE all player data? This action **cannot be undone.**\n"
            "Type `CONFIRM` in this channel within 30 seconds to proceed.",
            ephemeral=True
        )

        def check(msg):
            return (
                msg.author.id == interaction.user.id and
                msg.channel.id == interaction.channel_id and
                msg.content.strip().upper() == "CONFIRM"
            )

        try:
            msg = await self.bot.wait_for("message", timeout=30, check=check)
        except asyncio.TimeoutError:
            return await interaction.followup.send("⌛ Nuke cancelled — no confirmation received.", ephemeral=True)

        # Execute nuke
        try:
            os.makedirs("/mnt/data", exist_ok=True)  # Ensure directory exists

            data = await load_file(USER_DATA) or {}
            wiped = {}

            for uid, profile in data.items():
                wiped[uid] = {
                    "username": profile.get("username", "[unknown]"),
                    "coins": 0,
                    "stash": [],
                    "blueprints": [],
                    "crafted": [],
                    "tools": [],
                    "prestige": 0,
                    "prestige_points": 0,
                    "rank_level": 0,
                    "reinforcements": {},
                    "scavenge_count": 0,
                    "tasks_completed": 0,
                    "turnins_completed": 0,
                    "successful_raids": 0,
                    "boosts": []
                }

            await save_file(USER_DATA, wiped)
            print("✅ [warlabnuke] All profiles reset successfully.")
            await interaction.followup.send("💥 All player data has been reset. Wipe complete.", ephemeral=False)

        except Exception as e:
            print(f"❌ [warlabnuke] Failed to wipe data: {e}")
            await interaction.followup.send("❌ Failed to reset data. See logs for error.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(WarlabNuke(bot))
