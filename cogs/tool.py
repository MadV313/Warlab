# cogs/tool.py — Admin: Give or remove tools from a player

import discord
from discord.ext import commands
from discord import app_commands
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
TOOL_ITEMS = ["Hammer", "Saw", "Pliers"]

class ToolManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tool", description="Admin: Give or remove tools from a player")
    @app_commands.describe(
        user="Target player",
        action="Give or remove tools",
        item="Tool name (must be valid)",
        quantity="How many to give or remove"
    )
    async def tool(
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

        if item not in TOOL_ITEMS:
            await interaction.response.send_message(f"❌ Invalid tool. Choose from: {', '.join(TOOL_ITEMS)}", ephemeral=True)
            return

        profiles = await load_file(USER_DATA) or {}
        user_id = str(user.id)
        profile = profiles.get(user_id, {"inventory": []})

        if action == "give":
            for _ in range(quantity):
                profile["inventory"].append({"item": item, "rarity": "Admin"})

            await interaction.response.send_message(f"✅ Gave **{quantity}x {item}** to {user.mention}.", ephemeral=True)

        elif action == "remove":
            removed = 0
            new_inventory = []
            for entry in profile["inventory"]:
                if entry.get("item") == item and removed < quantity:
                    removed += 1
                    continue
                new_inventory.append(entry)

            profile["inventory"] = new_inventory
            await interaction.response.send_message(f"🗑 Removed **{removed}x {item}** from {user.mention}.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Invalid action. Use `give` or `remove`.", ephemeral=True)
            return

        profiles[user_id] = profile
        await save_file(USER_DATA, profiles)

async def setup(bot):
    await bot.add_cog(ToolManager(bot))
