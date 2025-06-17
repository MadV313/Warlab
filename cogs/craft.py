# cogs/craft.py — Dynamic blueprint crafting with single-message flow

import discord
from discord.ext import commands
from discord import app_commands
from collections import Counter

from utils.fileIO import load_file, save_file
from utils.inventory import has_required_parts, remove_parts
from utils.prestigeBonusHandler import can_craft_tactical, can_craft_explosives

USER_DATA       = "data/user_profiles.json"
RECIPE_DATA     = "data/item_recipes.json"
ARMOR_DATA      = "data/armor_blueprints.json"
EXPLOSIVE_DATA  = "data/explosive_blueprints.json"

# ────────────────────────────────────────────────────────────────
class CraftDropdown(discord.ui.Select):
    def __init__(self, user_id: str, options):
        self.user_id = user_id
        super().__init__(
            placeholder="Select a blueprint to craft…",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        # Ownership check ────────────────────────────
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("⚠️ Not your menu.", ephemeral=True)
            return

        item_name = self.values[0]            # clean: "Mlock"
        await interaction.response.defer(ephemeral=True)

        # Load data ─────────────────────────────────
        profiles   = await load_file(USER_DATA) or {}
        recipes    = await load_file(RECIPE_DATA) or {}
        armor      = await load_file(ARMOR_DATA) or {}
        explosives = await load_file(EXPLOSIVE_DATA) or {}
        user       = profiles.get(self.user_id)

        if not user:
            await interaction.response.edit_message(content="❌ Profile not found.", view=None)
            return

        # Blueprint ownership check
        if item_name not in user.get("blueprints", []):
            await interaction.response.edit_message(
                content=f"🔒 You must unlock **{item_name} Blueprint** first.",
                view=None
            )
            return

        item_key = item_name.lower()
        recipe   = recipes.get(item_key)
        if not recipe:
            await interaction.response.edit_message(content="❌ Unknown / invalid blueprint.", view=None)
            return

        # Prestige gates
        prestige = user.get("prestige", 0)
        if item_key in armor and not can_craft_tactical(prestige):
            await interaction.response.edit_message(content="🔒 Prestige II required for tactical gear.", view=None)
            return
        if item_key in explosives and not can_craft_explosives(prestige):
            await interaction.response.edit_message(content="🔒 Prestige III required for explosives.", view=None)
            return

        # Parts check
        stash_counter = Counter(user.get("stash", []))
        if not has_required_parts(stash_counter, recipe["requirements"]):
            missing = [
                f"{qty - stash_counter.get(p, 0)}× {p}"
                for p, qty in recipe["requirements"].items()
                if stash_counter.get(p, 0) < qty
            ]
            await interaction.response.edit_message(
                content="❌ Missing parts:\n• " + "\n• ".join(missing),
                view=None
            )
            return

        # Crafting ───────────────────────────────────
        remove_parts(user["stash"], recipe["requirements"])
        crafted = recipe["produces"]
        user["stash"].append(crafted)
        user.setdefault("crafted", []).append(crafted)
        profiles[self.user_id] = user
        await save_file(USER_DATA, profiles)

        embed = discord.Embed(
            title="✅ Crafting Successful",
            description=f"You crafted **{crafted}**!",
            color=0x2ecc71
        )
        embed.add_field(name="Type",   value=recipe.get("type",   "Unknown"), inline=True)
        embed.add_field(name="Rarity", value=recipe.get("rarity", "Common"),  inline=True)
        embed.set_footer(text="WARLAB | SV13 Bot")

        await interaction.response.edit_message(content="", embed=embed, view=None)

# ────────────────────────────────────────────────────────────────
class CraftView(discord.ui.View):
    def __init__(self, user_id: str, blueprints: list[str]):
        super().__init__(timeout=90)
        self.dropdown = CraftDropdown(user_id, [
            discord.SelectOption(label=f"{bp} Blueprint", value=bp)
            for bp in blueprints[:25]
        ])
        self.add_item(self.dropdown)

# ────────────────────────────────────────────────────────────────
class Craft(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="craft", description="Craft an item from your unlocked blueprints")
    async def craft(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        uid       = str(interaction.user.id)
        profiles  = await load_file(USER_DATA) or {}
        profile   = profiles.get(uid)

        if not profile:
            await interaction.followup.send("❌ You need a profile. Use `/register` first.", ephemeral=True)
            return

        blueprints = profile.get("blueprints", [])
        if not blueprints:
            await interaction.followup.send("🔒 You own no blueprints yet. Visit `/blackmarket`.", ephemeral=True)
            return

        await interaction.followup.send(
            "🛠️ Choose an item to craft:",
            view=CraftView(uid, blueprints),
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Craft(bot))
