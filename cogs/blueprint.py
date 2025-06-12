# cogs/blueprint.py — Admin: Give or remove blueprint unlocks

import discord
from discord.ext import commands
from discord import app_commands
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
KNOWN_BLUEPRINTS = [
    "M4 Blueprint", "AK-74 Blueprint", "Ghillie Suit Blueprint",
    "Field Backpack Blueprint", "Improvised Vest Blueprint",
    "Pox Explosive Blueprint", "Claymore Blueprint"
]

class BlueprintManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="blueprint", description="Admin: Give or remove blueprints from a player")
    @app_commands.describe(
        user="Target player",
        action="Give or remove blueprint",
        item="Blueprint name (must match list)",
        quantity="How many copies to add (ignored on removal)"
    )
    async def blueprint(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        action: str,
        item: str,
        quantity: int = 1
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You don’t have permission to use this.", ephemeral=True)
            return

        action = action.lower()
        item = item.strip()

        if item not in KNOWN_BLUEPRINTS:
            await interaction.response.send_message(f"❌ Invalid blueprint. Choose from: {', '.join(KNOWN_BLUEPRINTS)}", ephemeral=True)
            return

        profiles = await load_file(USER_DATA) or {}
        user_id = str(user.id)
        profile = profiles.get(user_id, {"inventory": [], "blueprints": []})
        blueprints = profile.get("blueprints", [])

        if action == "give":
            if item not in blueprints:
                blueprints.append(item)
            await interaction.response.send_message(f"✅ Blueprint **{item}** unlocked for {user.mention}.", ephemeral=True)

        elif action == "remove":
            if item in blueprints:
                blueprints.remove(item)
                await interaction.response.send_message(f"🗑 Blueprint **{item}** removed from {user.mention}.", ephemeral=True)
            else:
                await interaction.response.send_message(f"⚠️ {user.mention} does not have that blueprint.", ephemeral=True)
                return
        else:
            await interaction.response.send_message("❌ Invalid action. Use `give` or `remove`.", ephemeral=True)
            return

        profile["blueprints"] = blueprints
        profiles[user_id] = profile
        await save_file(USER_DATA, profiles)

async def setup(bot):
    await bot.add_cog(BlueprintManager(bot))
