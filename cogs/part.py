# cogs/part.py — Fully Inline /part Command with Dynamic Field Autocomplete

import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
GUN_PARTS = "data/item_recipes.json"
ARMOR_PARTS = "data/armor_blueprints.json"
EXPLOSIVE_PARTS = "data/explosive_blueprints.json"

CATEGORY_MAP = {
    "Weapons": GUN_PARTS,
    "Armor": ARMOR_PARTS,
    "Explosives": EXPLOSIVE_PARTS
}

class PartManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cached_parts = {}  # {"Weapons": [parts], ...}

    async def get_parts_by_category(self, category):
        if category in self.cached_parts:
            return self.cached_parts[category]

        data = await load_file(CATEGORY_MAP[category]) or {}
        part_set = set()
        for item in data.values():
            part_set.update(item.get("required_parts", []))

        self.cached_parts[category] = sorted(part_set)
        return self.cached_parts[category]

    @app_commands.command(name="part", description="Admin: Give or remove parts from a player.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        action="Give or remove a part",
        user="Target player",
        item="Category: Weapons, Armor, or Explosives",
        part="Part name from selected category",
        quantity="Amount to give or remove"
    )
    async def part(
        self,
        interaction: discord.Interaction,
        action: Literal["give", "remove"],
        user: discord.Member,
        item: Literal["Weapons", "Armor", "Explosives"],
        part: str,
        quantity: int
    ):
        await interaction.response.defer(ephemeral=True)

        if quantity <= 0:
            await interaction.followup.send("⚠️ Quantity must be greater than 0.", ephemeral=True)
            return

        valid_parts = await self.get_parts_by_category(item)
        if part not in valid_parts:
            await interaction.followup.send(
                f"❌ Invalid part for {item}. Try auto-completing the field.",
                ephemeral=True
            )
            return

        profiles = await load_file(USER_DATA) or {}
        uid = str(user.id)
        profile = profiles.get(uid, {})
        stash = profile.get("stash", [])
        if not isinstance(stash, list):
            stash = []

        # ── Action Logic ──
        if action == "give":
            stash.extend([part] * quantity)
            msg = f"✅ Gave **{quantity} × {part}** to {user.mention}."
        else:
            removed = 0
            new_stash = []
            for s in stash:
                if s == part and removed < quantity:
                    removed += 1
                    continue
                new_stash.append(s)
            stash = new_stash
            msg = (
                f"🗑 Removed **{removed} × {part}** from {user.mention}."
                if removed else
                f"⚠️ {user.mention} doesn't have that many **{part}**."
            )

        profile["stash"] = stash
        profiles[uid] = profile
        await save_file(USER_DATA, profiles)
        await interaction.followup.send(msg, ephemeral=True)

    @part.autocomplete("part")
    async def autocomplete_part(self, interaction: discord.Interaction, current: str):
        item_category = interaction.namespace.item
        if not item_category:
            return []

        parts = await self.get_parts_by_category(item_category)
        return [
            app_commands.Choice(name=p, value=p)
            for p in parts if current.lower() in p.lower()
        ][:25]

async def setup(bot):
    await bot.add_cog(PartManager(bot))
