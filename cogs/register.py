import discord
from discord.ext import commands
from discord import app_commands, Interaction

from utils.profileManager import create_profile, get_profile

class RegisterCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # slash command
    @app_commands.command(name="register", description="Create your Warlab profile.")
    async def register(self, interaction: Interaction):
        uid = str(interaction.user.id)
        existing = get_profile(uid)
        if existing:
            await interaction.response.send_message(
                "✅ You already have a profile — you can now try all other /warlab comands!",
                ephemeral=True
            )
            return

        create_profile(uid, interaction.user.display_name)
        await interaction.response.send_message(
            "🔗 Profile created! You can now use commands like /scavenge or /rank.",
            ephemeral=True
        )

# required setup() for a cog
async def setup(bot: commands.Bot):
    await bot.add_cog(RegisterCog(bot))
