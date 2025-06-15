# cogs/part.py — Admin: Give or remove parts/materials from a player (dropdowns)

import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
GUN_PARTS = "data/item_recipes.json"
ARMOR_PARTS = "data/armor_blueprints.json"

class PartDropdown(discord.ui.Select):
    def __init__(self, parts, item_name, action, user, quantity):
        options = [
            discord.SelectOption(label=part, value=part)
            for part in parts
        ]
        super().__init__(placeholder="Select a part to give or remove...", min_values=1, max_values=1, options=options)
        self.item_name = item_name
        self.action = action
        self.user = user
        self.quantity = quantity

    async def callback(self, interaction: discord.Interaction):
        part = self.values[0]
        profiles = await load_file(USER_DATA) or {}
        user_id = str(self.user.id)
        profile = profiles.get(user_id, {"inventory": []})

        if self.action == "give":
            for _ in range(self.quantity):
                profile["inventory"].append({"item": part, "rarity": "Admin"})
            await interaction.response.send_message(f"✅ Gave **{self.quantity}x {part}** to {self.user.mention}.", ephemeral=True)

        elif self.action == "remove":
            removed = 0
            new_inventory = []
            for entry in profile["inventory"]:
                if entry.get("item") == part and removed < self.quantity:
                    removed += 1
                    continue
                new_inventory.append(entry)
            profile["inventory"] = new_inventory
            await interaction.response.send_message(f"🗑 Removed **{removed}x {part}** from {self.user.mention}.", ephemeral=True)

        profiles[user_id] = profile
        await save_file(USER_DATA, profiles)

class ItemDropdown(discord.ui.Select):
    def __init__(self, item_parts_map, action, user, quantity):
        options = [
            discord.SelectOption(label=item, value=item)
            for item in item_parts_map.keys()
        ]
        super().__init__(placeholder="Select a base item (gun/armor)...", min_values=1, max_values=1, options=options)
        self.item_parts_map = item_parts_map
        self.action = action
        self.user = user
        self.quantity = quantity

    async def callback(self, interaction: discord.Interaction):
        item = self.values[0]
        parts = self.item_parts_map[item]
        view = discord.ui.View()
        view.add_item(PartDropdown(parts, item, self.action, self.user, self.quantity))
        await interaction.response.send_message(f"Now select a part from **{item}**:", view=view, ephemeral=True)

class PartManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="part", description="Admin: Give or remove parts from a player")
    @app_commands.describe(
        user="Target player",
        action="Give or remove parts",
        quantity="How many to give or remove"
    )
    async def part(self, interaction: discord.Interaction, user: discord.Member, action: Literal["give", "remove"], quantity: int = 1):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You don’t have permission to use this.", ephemeral=True)
            return

        guns = await load_file(GUN_PARTS) or {}
        armors = await load_file(ARMOR_PARTS) or {}
        item_parts_map = {}

        for data in guns.values():
            name = data.get("produces")
            parts = data.get("required_parts", [])
            if name and parts:
                item_parts_map[name] = parts

        for data in armors.values():
            name = data.get("produces")
            parts = data.get("required_parts", [])
            if name and parts:
                item_parts_map[name] = parts

        if not item_parts_map:
            await interaction.response.send_message("❌ No part data found.", ephemeral=True)
            return

        view = discord.ui.View()
        view.add_item(ItemDropdown(item_parts_map, action, user, quantity))
        await interaction.response.send_message("Select a base item to begin:", view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(PartManager(bot))
