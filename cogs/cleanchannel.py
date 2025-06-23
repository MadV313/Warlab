import discord
from discord.ext import commands
from discord import app_commands
import traceback

ADMIN_ROLE_ID = 1173049392371085392
WARLAB_CHANNEL_ID = 1382187883590455296

class CleanChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ [COG LOADED] CleanChannel cog loaded successfully.")

    def is_admin():
        async def predicate(interaction: discord.Interaction):
            print(f"🔐 [Check] is_admin called by {interaction.user}")
            return any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles)
        return app_commands.check(predicate)

    @app_commands.command(name="cleanchannel", description="Admin: Wipe WARLAB channel after confirmation.")
    @is_admin()
    async def cleanchannel(self, interaction: discord.Interaction):
        print(f"📥 [/cleanchannel] Triggered by {interaction.user} in channel {interaction.channel.id}")

        if interaction.channel.id != WARLAB_CHANNEL_ID:
            print("❌ Incorrect channel")
            await interaction.response.send_message("❌ This command can only be used in the WARLAB channel.", ephemeral=True)
            return

        class ConfirmView(discord.ui.View):
            def __init__(self, author: discord.Member):
                super().__init__(timeout=30)
                self.author = author

            async def interaction_check(self, i: discord.Interaction) -> bool:
                print(f"🔁 [Interaction Check] Pressed by {i.user}")
                if i.user.id != self.author.id:
                    await i.response.send_message("❌ Only the command user may confirm/cancel.", ephemeral=True)
                    return False
                return True

            @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.danger)
            async def confirm(self, i: discord.Interaction, _):
                print(f"⚠️ Confirm pressed by {i.user}")
                await i.response.defer(ephemeral=True)
                try:
                    deleted = await i.channel.purge(limit=100)
                    await i.followup.send(f"🧹 Deleted {len(deleted)} messages.", ephemeral=True)
                    print(f"✅ Channel cleaned. {len(deleted)} messages removed.")
                except Exception as e:
                    print(f"❌ Exception during purge: {e}")
                    traceback.print_exc()
                    await i.followup.send("❌ Purge failed. Check logs.", ephemeral=True)
                self.stop()

            @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, i: discord.Interaction, _):
                print(f"🚫 Cancel pressed by {i.user}")
                await i.response.send_message("❌ Cancelled.", ephemeral=True)
                self.stop()

        try:
            await interaction.response.send_message(
                "⚠️ Are you sure you want to clean this channel? This will delete up to 100 messages.",
                view=ConfirmView(interaction.user),
                ephemeral=True
            )
            print("✅ Confirmation prompt sent.")
        except Exception as e:
            print(f"❌ Failed to send prompt: {e}")
            traceback.print_exc()

# 🔧 Catch any Cog load failures
async def setup(bot):
    try:
        await bot.add_cog(CleanChannel(bot))
        print("✅ [SETUP] CleanChannel setup complete.")
    except Exception as e:
        print(f"❌ [SETUP FAILED] cleanchannel.py: {e}")
        traceback.print_exc()
