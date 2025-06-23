# cogs/register.py — Creates player profile if not already registered

import discord
from discord.ext import commands
from discord import app_commands, Interaction

from utils.profileManager import create_profile, get_profile

class RegisterCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="register", description="Create your Warlab profile.")
    async def register(self, interaction: Interaction):
        uid = str(interaction.user.id)
        existing = await get_profile(uid)

        print(f"📥 [/register] Called by: {interaction.user} ({uid})")

        if existing:
            print(f"✅ [/register] Profile already exists for {uid}.")
            await interaction.response.send_message(
                "✅ You already have a profile — you can now try all other /warlab commands!",
                ephemeral=True
            )
            return

        create_profile(uid, interaction.user.display_name)
        print(f"🆕 [/register] Created new profile for {uid} — {interaction.user.display_name}")
        await interaction.response.send_message(
            "🔗 Profile created! You can now use all other /warlab commands like /scavenge, /rank, etc.",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(RegisterCog(bot))
