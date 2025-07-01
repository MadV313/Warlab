import discord
from discord.ext import commands
from discord import app_commands
import os
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
WARLAB_CHANNEL_ID = 1382187883590455296     # Replace with your actual Warlab channel ID
BACKUP_CHANNEL_ID = 1389706195102728322     # Backup upload channel
ADMIN_ROLE_IDS = ["1173049392371085392", "1184921037830373468"]  # Your admin role IDs

class WarlabBackup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="warlabbackup", description="🧪 ADMIN: Back up all Warlab user data to the secure archive channel.")
    @app_commands.guilds(discord.Object(id=1166441420643639348))  # Replace with your server ID
    async def warlabbackup(self, interaction: discord.Interaction):
        print(f"📦 [warlabbackup] Called by {interaction.user} ({interaction.user.id})")

        # Channel restriction
        if interaction.channel_id != WARLAB_CHANNEL_ID:
            return await interaction.response.send_message(
                "❌ This command must be used in the Warlab channel.", ephemeral=True
            )

        # Admin role restriction
        user_roles = [role.id for role in interaction.user.roles]
        if not any(role_id in ADMIN_ROLE_IDS for role_id in user_roles):
            return await interaction.response.send_message(
                "❌ You do not have permission to use this command.", ephemeral=True
            )

        await interaction.response.send_message("📁 Creating backup...", ephemeral=True)

        try:
            # Load and save a clean local copy
            profiles = await load_file(USER_DATA) or {}
            backup_path = f"/mnt/data/user_profiles_backup.json"
            with open(backup_path, "w", encoding="utf-8") as f:
                import json
                json.dump(profiles, f, indent=2)

            # Send to backup channel
            backup_channel = self.bot.get_channel(BACKUP_CHANNEL_ID)
            if backup_channel:
                await backup_channel.send(
                    content=f"📦 **Warlab backup** by <@{interaction.user.id}> — full export of `user_profiles.json`",
                    file=discord.File(backup_path)
                )
                await interaction.followup.send("✅ Backup completed and sent to the archive channel.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Backup channel not found.", ephemeral=True)
                print(f"❌ [warlabbackup] Could not find channel: {BACKUP_CHANNEL_ID}")

        except Exception as e:
            print(f"❌ [warlabbackup] Backup failed: {e}")
            await interaction.followup.send("❌ Backup failed. Check logs for details.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(WarlabBackup(bot))
