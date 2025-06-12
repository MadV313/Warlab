# cogs/part.py — Admin: Give or remove parts/materials from a player

import discord
from discord.ext import commands
from discord import app_commands
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
PART_ITEMS = [
    "Nails", "Wood Plank", "Scrap Metal", "Duct Tape",
    "Screwdriver", "Wrench", "Suppressor"
]

class PartManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="part", description="Admin: Give or remove parts from a player")
    @app_commands.describe(
        user="Target player",
        action="Give or remove parts",
        item="Part name (must match system list)",
        quantity="How many to give or remove"
    )
    async def part(
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

        if item not in PART_ITEMS:
            await interaction.response.send_message(f"❌ Invalid part. Choose from: {', '.join(PART_ITEMS)}", ephemeral=True)
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
    await bot.add_cog(PartManager(bot))
