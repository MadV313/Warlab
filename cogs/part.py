# cogs/part.py — Admin: Give or remove parts from a player (with category dropdown)

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

class PartDropdown(discord.ui.Select):
    def __init__(self, category, callback_fn):
        self.category = category
        self.callback_fn = callback_fn
        super().__init__(placeholder="Select a part...", min_values=1, max_values=1, options=[])

    async def update_options(self):
        data = await load_file(CATEGORY_MAP[self.category]) or {}
        all_parts = set()
        for item in data.values():
            all_parts.update(item.get("required_parts", []))
        self.options = [discord.SelectOption(label=part, value=part) for part in sorted(all_parts)]

    async def callback(self, interaction: discord.Interaction):
        await self.callback_fn(interaction, self.values[0])

class CategoryDropdown(discord.ui.Select):
    def __init__(self, callback_fn):
        self.callback_fn = callback_fn
        options = [
            discord.SelectOption(label="Weapons", value="Weapons"),
            discord.SelectOption(label="Armor", value="Armor"),
            discord.SelectOption(label="Explosives", value="Explosives")
        ]
        super().__init__(placeholder="Choose category", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await self.callback_fn(interaction, self.values[0])

class PartSelectionView(discord.ui.View):
    def __init__(self, action, user, quantity):
        super().__init__(timeout=60)
        self.action = action
        self.user = user
        self.quantity = quantity
        self.part = None
        self.add_item(CategoryDropdown(self.category_chosen))

    async def category_chosen(self, interaction, category):
        self.clear_items()
        part_selector = PartDropdown(category, self.part_chosen)
        await part_selector.update_options()
        self.add_item(part_selector)
        await interaction.response.edit_message(content=f"🔧 Select a part from **{category}**", view=self)

    async def part_chosen(self, interaction, part):
        self.part = part
        await self.execute(interaction)

    async def execute(self, interaction):
        profiles = await load_file(USER_DATA) or {}
        uid = str(self.user.id)
        profile = profiles.get(uid, {})
        stash = profile.get("stash", [])

        if not isinstance(stash, list):
            stash = []

        if self.action == "give":
            stash.extend([self.part] * self.quantity)
            msg = f"✅ Gave **{self.quantity} × {self.part}** to {self.user.mention}."
        else:
            removed = 0
            new_stash = []
            for s in stash:
                if s == self.part and removed < self.quantity:
                    removed += 1
                    continue
                new_stash.append(s)
            stash = new_stash
            msg = (
                f"🗑 Removed **{removed} × {self.part}** from {self.user.mention}."
                if removed else
                f"⚠️ {self.user.mention} doesn't have that many **{self.part}**."
            )

        profile["stash"] = stash
        profiles[uid] = profile
        await save_file(USER_DATA, profiles)
        await interaction.response.edit_message(content=msg, view=None)

class PartManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="part", description="Admin: Give or remove parts from a player.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        action="Give or remove a part",
        user="Target player",
        quantity="How many to give or remove"
    )
    async def part(
        self,
        interaction: discord.Interaction,
        action: Literal["give", "remove"],
        user: discord.Member,
        quantity: int
    ):
        await interaction.response.defer(ephemeral=True)
        if quantity <= 0:
            await interaction.followup.send("⚠️ Quantity must be greater than **0**.", ephemeral=True)
            return

        view = PartSelectionView(action, user, quantity)
        await interaction.followup.send("📦 Select a category to begin:", view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(PartManager(bot))
