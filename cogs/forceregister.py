import discord
from discord.ext import commands
from discord import app_commands
from utils.storageClient import load_file, save_file

USER_DATA = "data/user_profiles.json"
ADMIN_ROLE_ID = 1173049392371085392

class ForceRegister(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_admin():
        async def predicate(interaction: discord.Interaction):
            return any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles)
        return app_commands.check(predicate)

    @app_commands.command(name="forceregister", description="Admin: Force-register a player manually.")
    @is_admin()
    async def forceregister(self, interaction: discord.Interaction, target: discord.Member):
        user_id = str(target.id)
        profiles = await load_file(USER_DATA) or {}

        if user_id in profiles:
            await interaction.response.send_message(f"🟡 `{target.display_name}` is already registered.", ephemeral=True)
            return

        profiles[user_id] = {
            "id": user_id,
            "name": target.display_name,
            "stash": [],
            "coins": 0,
            "prestige": 0,
            "reinforcements": {},
            "stash_hp": 0
        }

        await save_file(USER_DATA, profiles)
        await interaction.response.send_message(f"✅ `{target.display_name}` has been force-registered.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ForceRegister(bot))
