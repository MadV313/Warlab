# cogs/part.py — Unified Category → Part → Quantity Selection in One Flow

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

class PartSelect(discord.ui.View):
    def __init__(self, interaction, action: str, target_user: discord.Member, quantity: int):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.action = action
        self.target_user = target_user
        self.quantity = quantity
        self.selected_category = None
        self.selected_part = None

        self.category_select = discord.ui.Select(
            placeholder="Select part category...",
            options=[
                discord.SelectOption(label="Weapons", value="Weapons"),
                discord.SelectOption(label="Armor", value="Armor"),
                discord.SelectOption(label="Explosives", value="Explosives")
            ]
        )
        self.category_select.callback = self.category_chosen
        self.add_item(self.category_select)

    async def category_chosen(self, interaction: discord.Interaction):
        self.selected_category = self.category_select.values[0]
        self.clear_items()

        # Load all parts under that category
        part_file = CATEGORY_MAP[self.selected_category]
        raw = await load_file(part_file) or {}
        part_set = set()
        for entry in raw.values():
            part_set.update(entry.get("required_parts", []))

        self.part_select = discord.ui.Select(
            placeholder=f"Select a part from {self.selected_category}...",
            options=[discord.SelectOption(label=p, value=p) for p in sorted(part_set)]
        )
        self.part_select.callback = self.part_chosen
        self.add_item(self.part_select)

        await interaction.response.edit_message(content="🔧 Now pick the part:", view=self)

    async def part_chosen(self, interaction: discord.Interaction):
        self.selected_part = self.part_select.values[0]
        await self.execute(interaction)

    async def execute(self, interaction: discord.Interaction):
        profiles = await load_file(USER_DATA) or {}
        uid = str(self.target_user.id)
        profile = profiles.get(uid, {})
        stash = profile.get("stash", [])

        if not isinstance(stash, list):
            stash = []

        # Perform action
        if self.action == "give":
            stash.extend([self.selected_part] * self.quantity)
            msg = f"✅ Gave **{self.quantity} × {self.selected_part}** to {self.target_user.mention}."
        else:
            removed = 0
            new_stash = []
            for item in stash:
                if item == self.selected_part and removed < self.quantity:
                    removed += 1
                    continue
                new_stash.append(item)
            stash = new_stash
            msg = (
                f"🗑 Removed **{removed} × {self.selected_part}** from {self.target_user.mention}."
                if removed else
                f"⚠️ Not enough **{self.selected_part}** to remove."
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
        quantity="Amount to give or remove"
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
            await interaction.followup.send("⚠️ Quantity must be more than **0**.", ephemeral=True)
            return

        view = PartSelect(interaction, action, user, quantity)
        await interaction.followup.send(
            f"🔧 Choose a part category to **{action}** to {user.mention}:",
            view=view,
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(PartManager(bot))
