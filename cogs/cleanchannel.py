import discord
from discord.ext import commands
from discord import app_commands
import traceback

ADMIN_ROLE_ID = 1173049392371085392
WARLAB_CHANNEL_ID = 1382187883590455296

class CleanChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_admin():
        async def predicate(interaction: discord.Interaction):
            return any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles)
        return app_commands.check(predicate)

    @app_commands.command(name="cleanchannel", description="Admin: Wipe WARLAB channel after confirmation.")
    @is_admin()
    async def cleanchannel(self, interaction: discord.Interaction):
        print(f"📥 [/cleanchannel] Command used by {interaction.user} ({interaction.user.id})")

        if interaction.channel.id != WARLAB_CHANNEL_ID:
            print(f"❌ [cleanchannel] Rejected: Wrong channel ({interaction.channel.id})")
            await interaction.response.send_message("❌ This command can only be used in the WARLAB channel.", ephemeral=True)
            return

        class ConfirmView(discord.ui.View):
            def __init__(self, author: discord.Member):
                super().__init__(timeout=30)
                self.author = author

            async def interaction_check(self, i: discord.Interaction) -> bool:
                if i.user.id != self.author.id:
                    await i.response.send_message("❌ Only the original command user can confirm or cancel.", ephemeral=True)
                    print(f"⚠️ [cleanchannel] Unauthorized button press by {i.user} ({i.user.id})")
                    return False
                return True

            @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.danger)
            async def confirm(self, i: discord.Interaction, _):
                await i.response.defer(ephemeral=True)
                try:
                    deleted = await i.channel.purge(limit=100)
                    print(f"🧹 [cleanchannel] Deleted {len(deleted)} messages in {i.channel.name}")
                    await i.followup.send(f"🧹 Channel cleaned. `{len(deleted)}` messages purged.", ephemeral=True)
                except Exception as e:
                    print(f"❌ [cleanchannel] Purge failed: {e}")
                    traceback.print_exc()
                    await i.followup.send("❌ Failed to clean the channel. Check logs for details.", ephemeral=True)
                self.stop()

            @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, i: discord.Interaction, _):
                await i.response.send_message("❌ Cleanup cancelled.", ephemeral=True)
                print(f"🚫 [cleanchannel] Cleanup cancelled by {i.user}")
                self.stop()

        try:
            await interaction.response.send_message(
                "⚠️ Are you sure you want to clean this channel? This will delete up to 100 messages.",
                view=ConfirmView(interaction.user),
                ephemeral=True
            )
            print("✅ [cleanchannel] Confirmation prompt sent.")
        except Exception as e:
            print(f"❌ [cleanchannel] Failed to send confirmation prompt: {e}")
            traceback.print_exc()

async def setup(bot):
    await bot.add_cog(CleanChannel(bot))
