import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
WARLAB_CHANNEL_ID = 1382187883590455296  # Warlab channel ID

class ConfirmButton(discord.ui.View):
    def __init__(self, author_id, timeout=30):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.confirmed = asyncio.Event()

    @discord.ui.button(label="CONFIRM", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You are not authorized to confirm this action.", ephemeral=True)
            return
        await interaction.response.send_message("☢️ Confirmed. Nuking player data...", ephemeral=True)
        self.confirmed.set()
        self.stop()

class WarlabNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="warlabnuke", description="☢️ ADMIN: Reset all Warlab player data!")
    @app_commands.guilds(discord.Object(id=1166441420643639348))
    @app_commands.checks.has_permissions(administrator=True)
    async def warlabnuke(self, interaction: discord.Interaction):
        print(f"☢️ [warlabnuke] Called by {interaction.user} ({interaction.user.id})")

        if interaction.channel_id != WARLAB_CHANNEL_ID:
            return await interaction.response.send_message(
                "❌ This command can only be used in the Warlab channel.", ephemeral=True
            )

        view = ConfirmButton(author_id=interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Are you **sure** you want to **NUKE** all player data?\n"
            "This action **cannot be undone**. Click **CONFIRM** within 30 seconds.",
            view=view,
            ephemeral=True
        )

        try:
            await view.confirmed.wait()
        except asyncio.TimeoutError:
            await interaction.followup.send("⌛ Nuke cancelled — no confirmation received.", ephemeral=True)
            return

        try:
            os.makedirs("/mnt/data", exist_ok=True)
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
            await interaction.followup.send("💥 All player data has been **reset**. Wipe complete.", ephemeral=True)

        except Exception as e:
            print(f"❌ [warlabnuke] Failed to wipe data: {e}")
            await interaction.followup.send("❌ Failed to reset data. See logs for error.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(WarlabNuke(bot))
