import discord
from discord.ext import commands
from discord import app_commands
import traceback

ADMIN_ROLE_ID = 1173049392371085392
WARLAB_CHANNEL_ID = 1382187883590455296

# 🔘 View class MUST be top-level to avoid callback binding issues
class ConfirmView(discord.ui.View):
    def __init__(self, author: discord.Member):
        super().__init__(timeout=30)
        self.author = author

    async def interaction_check(self, i: discord.Interaction) -> bool:
        print(f"🔁 [Interaction Check] Pressed by {i.user}")
        if i.user.id != self.author.id:
            await i.response.send_message("❌ Only the original user may confirm/cancel.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, _):
        print(f"⚠️ Confirm button pressed by {interaction.user}")
        await interaction.response.defer(ephemeral=True)
        try:
            deleted = await interaction.channel.purge(limit=100)
            await interaction.followup.send(f"🧹 Deleted {len(deleted)} messages.", ephemeral=True)
            print(f"✅ Channel cleaned. {len(deleted)} messages removed.")
        except Exception as e:
            print(f"❌ Purge failed: {e}")
            traceback.print_exc()
            await interaction.followup.send("❌ Failed to purge messages.", ephemeral=True)
        self.stop()

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, _):
        print(f"🚫 Cancel button pressed by {interaction.user}")
        await interaction.response.send_message("❌ Channel cleanup cancelled.", ephemeral=True)
        self.stop()

class CleanChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ [COG LOADED] CleanChannel")

    def is_admin():
        async def predicate(interaction: discord.Interaction):
            print(f"🔐 [Check] is_admin called by {interaction.user}")
            return any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles)
        return app_commands.check(predicate)

    @app_commands.command(name="cleanchannel", description="Admin: Wipe WARLAB channel after confirmation.")
    @is_admin()
    async def cleanchannel(self, interaction: discord.Interaction):
        print(f"🟢 /cleanchannel by {interaction.user} ({interaction.user.id})")

        if interaction.channel.id != WARLAB_CHANNEL_ID:
            print("❌ Not in WARLAB channel")
            await interaction.response.send_message("❌ This command can only be used in the WARLAB channel.", ephemeral=True)
            return

        try:
            await interaction.response.send_message(
                "⚠️ Are you sure you want to clean this channel? This will delete up to 100 messages.",
                view=ConfirmView(interaction.user),
                ephemeral=True
            )
            print("✅ Confirmation view sent.")
        except Exception as e:
            print(f"❌ Failed to send confirmation view: {e}")
            traceback.print_exc()

async def setup(bot):
    try:
        await bot.add_cog(CleanChannel(bot))
        print("✅ [SETUP] CleanChannel loaded.")
    except Exception as e:
        print(f"❌ [SETUP FAILED] CleanChannel: {e}")
        traceback.print_exc()
