import discord
from discord.ext import commands
from discord import app_commands
from utils.profileManager import create_profile, get_profile  # ✅ Use proper profile functions

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
        print(f"📥 [/forceregister] Called by {interaction.user} for target {target} ({user_id})")

        existing = await get_profile(user_id)
        if existing:
            print(f"🟡 [forceregister] {target.display_name} already registered.")
            await interaction.response.send_message(
                f"🟡 `{target.display_name}` is already registered.",
                ephemeral=True
            )
            return

        await create_profile(user_id, target.display_name)
        print(f"✅ [forceregister] {target.display_name} successfully registered.")
        await interaction.response.send_message(
            f"✅ `{target.display_name}` has been force-registered.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(ForceRegister(bot))
