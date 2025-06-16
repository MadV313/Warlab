# cogs/part.py — Admin: Give or remove parts/materials from a player (Blueprint-Style)

import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
GUN_PARTS = "data/item_recipes.json"
ARMOR_PARTS = "data/armor_blueprints.json"

class PartManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_all_parts(self):
        guns = await load_file(GUN_PARTS) or {}
        armors = await load_file(ARMOR_PARTS) or {}

        parts = set()
        for data in list(guns.values()) + list(armors.values()):
            for p in data.get("required_parts", []):
                parts.add(p)

        return sorted(parts)

    @app_commands.command(name="part", description="Admin: Give or remove parts from a player.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        action="Give or remove a part",
        user="Target player",
        item="Name of the part/material",
        quantity="How many to give or remove"
    )
    async def part(
        self,
        interaction: discord.Interaction,
        action: Literal["give", "remove"],
        user: discord.Member,
        item: str,
        quantity: int
    ):
        if quantity <= 0 and action == "give":
            await interaction.response.send_message("⚠️ Quantity must be greater than 0.", ephemeral=True)
            return

        item = item.strip()
        valid_parts = await self.get_all_parts()
        if item not in valid_parts:
            await interaction.response.send_message(
                f"❌ Invalid part.\nChoose from: {', '.join(valid_parts)}",
                ephemeral=True
            )
            return

        profiles = await load_file(USER_DATA) or {}
        user_id = str(user.id)
        profile = profiles.get(user_id, {"inventory": []})

        # ── Give ────────────────────────────────────────────────
        if action == "give":
            for _ in range(quantity):
                profile["inventory"].append({"item": item, "rarity": "Admin"})
            await interaction.response.send_message(
                f"✅ Gave **{quantity}× {item}** to {user.mention}.",
                ephemeral=True
            )

        # ── Remove ──────────────────────────────────────────────
        elif action == "remove":
            removed = 0
            new_inv = []
            for entry in profile["inventory"]:
                if entry.get("item") == item and removed < quantity:
                    removed += 1
                    continue
                new_inv.append(entry)

            profile["inventory"] = new_inv
            if removed > 0:
                await interaction.response.send_message(
                    f"🗑 Removed **{removed}× {item}** from {user.mention}.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"⚠️ {user.mention} does not have that part or not enough to remove.",
                    ephemeral=True
                )

        profiles[user_id] = profile
        await save_file(USER_DATA, profiles)

    @part.autocomplete("item")
    async def autocomplete_item(self, interaction: discord.Interaction, current: str):
        all_parts = await self.get_all_parts()
        return [
            app_commands.Choice(name=p, value=p)
            for p in all_parts if current.lower() in p.lower()
        ][:25]

async def setup(bot):
    await bot.add_cog(PartManager(bot))
