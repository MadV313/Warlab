import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import time
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
WARLAB_CHANNEL_ID = 1382187883590455296

class ConfirmButton(discord.ui.View):
    def __init__(self, author_id, timeout=30):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.confirmed = asyncio.Event()

    @discord.ui.button(label="CONFIRM", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Only the initiator can confirm this action.", ephemeral=True)
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
            return await interaction.followup.send("⌛ Nuke cancelled — no confirmation received.", ephemeral=True)

        try:
            data = await load_file(USER_DATA) or {}
            wiped = {}

            for uid, profile in data.items():
                wiped[uid] = {
                    "username": profile.get("username", "[unknown]"),
                    "coins": 0,
                    "materials": {},
                    "blueprints": [],
                    "tools": [],
                    "prestige": 0,
                    "rank_level": 0,
                    "builds_completed": 0,
                    "turnins": 0,
                    "boosts": {},
                    "reinforcements": {},
                    "task_status": "not_started",
                    "baseImage": profile.get("baseImage", "base_house.png"),
                    "created": profile.get("created", str(int(time.time())))
                }

            await save_file(USER_DATA, wiped)
            print("✅ [warlabnuke] All profiles reset but structure preserved.")
            await interaction.followup.send("💥 All player data wiped. Structure preserved. Ready to continue.", ephemeral=True)

        except Exception as e:
            print(f"❌ [warlabnuke] Failed: {e}")
            await interaction.followup.send("❌ Wipe failed — see logs for details.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(WarlabNuke(bot))
