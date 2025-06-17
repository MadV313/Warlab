# cogs/craft.py — Button-based blueprint crafting with single-message response

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

# 🔘 Craft Button (1 per blueprint)
class CraftButton(discord.ui.Button):
    def __init__(self, user_id, blueprint, enabled=True):
        self.user_id = user_id
        self.blueprint = blueprint
        label = f"🛠️ {blueprint}"
        super().__init__(
            label=label,
            style=discord.ButtonStyle.success if enabled else discord.ButtonStyle.secondary,
            disabled=not enabled
        )

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("⚠️ This isn’t your crafting menu.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Load files
        profiles   = await load_file(USER_DATA) or {}
        recipes    = await load_file(RECIPE_DATA) or {}
        armor      = await load_file(ARMOR_DATA) or {}
        explosives = await load_file(EXPLOSIVE_DATA) or {}
        user       = profiles.get(self.user_id)
        all_recipes = {**recipes, **armor, **explosives}

        if not user:
            await interaction.followup.send("❌ User profile not found.", ephemeral=True)
            return

        blueprint = self.blueprint
        item_key  = blueprint.lower()
        recipe    = all_recipes.get(item_key)

        if not recipe:
            await interaction.followup.send("❌ Invalid blueprint data.", ephemeral=True)
            return

        # Prestige gates
        prestige = user.get("prestige", 0)
        if item_key in armor and not can_craft_tactical(prestige):
            await interaction.followup.send("🔒 Requires Prestige II for tactical gear.", ephemeral=True)
            return
        if item_key in explosives and not can_craft_explosives(prestige):
            await interaction.followup.send("🔒 Requires Prestige III for explosives.", ephemeral=True)
            return

        # Inventory check
        stash = Counter(user.get("stash", []))
        if not has_required_parts(stash, recipe["requirements"]):
            missing = [
                f"{qty - stash.get(p, 0)}× {p}"
                for p, qty in recipe["requirements"].items()
                if stash.get(p, 0) < qty
            ]
            await interaction.followup.send(
                "❌ Missing parts:\n• " + "\n• ".join(missing),
                ephemeral=True
            )
            return

        # Craft it
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

        await interaction.followup.send(embed=embed, ephemeral=True)

# ❌ Close button
class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close", style=discord.ButtonStyle.danger, row=4)

    async def callback(self, interaction: discord.Interaction):
        for msg in getattr(self.view, "stored_messages", []):
            await msg.edit(content="❌ Crafting closed.", embed=None, view=None)
        await interaction.response.defer()

# 🧰 View: shows craftable and locked buttons
class CraftView(discord.ui.View):
    def __init__(self, user_id, blueprints, stash_counter, all_recipes):
        super().__init__(timeout=90)
        self.stored_messages = []

        count = 0
        for bp in blueprints:
            key = bp.lower()
            recipe = all_recipes.get(key)
            if not recipe:
                continue

            reqs = recipe.get("requirements", {})
            can_build = all(stash_counter.get(p, 0) >= q for p, q in reqs.items())
            self.add_item(CraftButton(user_id, bp, enabled=can_build))

            count += 1
            if count >= 20:
                break

        self.add_item(CloseButton())

# 📘 Slash Command Entry
class Craft(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="craft", description="Craft an item from your unlocked blueprints")
    async def craft(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        uid = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        recipes  = await load_file(RECIPE_DATA) or {}
        armor    = await load_file(ARMOR_DATA) or {}
        explosives = await load_file(EXPLOSIVE_DATA) or {}

        user = profiles.get(uid)
        if not user:
            await interaction.followup.send("❌ You need a profile. Use `/register` first.", ephemeral=True)
            return

        blueprints = user.get("blueprints", [])
        if not blueprints:
            await interaction.followup.send("🔒 You don’t own any blueprints. Visit `/blackmarket`.", ephemeral=True)
            return

        stash = Counter(user.get("stash", []))
        all_recipes = {**recipes, **armor, **explosives}

        embed = discord.Embed(
            title=f"🔧 {interaction.user.display_name}'s Blueprint Workshop",
            description="Click an item below to craft it if you have the parts.",
            color=0xf1c40f
        )
        embed.set_footer(text="WARLAB | SV13 Bot")

        view = CraftView(uid, blueprints, stash, all_recipes)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        sent = await interaction.original_response()
        view.stored_messages = [sent]

async def setup(bot):
    await bot.add_cog(Craft(bot))
