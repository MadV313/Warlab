import discord
from discord.ext import commands
from discord import app_commands
from utils.storageClient import load_file, save_file
from utils.profileManager import get_profile  # ✅ Consistent with registration logic

USER_DATA = "data/user_profiles.json"
ADMIN_ROLE_ID = 1173049392371085392

class ForceUnregister(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_admin():
        async def predicate(interaction: discord.Interaction):
            return any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles)
        return app_commands.check(predicate)

    @app_commands.command(name="forceunregister", description="Admin: Remove a player's profile.")
    @is_admin()
    async def forceunregister(self, interaction: discord.Interaction, target: discord.Member):
        user_id = str(target.id)
        print(f"📥 [/forceunregister] Called by {interaction.user} to remove {target} ({user_id})")

        profiles = await load_file(USER_DATA) or {}
        existing = await get_profile(user_id)

        if not existing:
            print(f"⚠️ [forceunregister] {target.display_name} has no profile.")
            await interaction.response.send_message(
                f"⚠️ `{target.display_name}` is not registered.",
                ephemeral=True
            )
            return

        del profiles[user_id]
        await save_file(USER_DATA, profiles)
        print(f"🗑️ [forceunregister] Removed profile for {target.display_name}")
        await interaction.response.send_message(
            f"🗑️ `{target.display_name}` has been unregistered.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(ForceUnregister(bot))
