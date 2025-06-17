# cogs/craft.py — Dynamic blueprint crafting with dropdown-only flow

import discord
from discord.ext import commands
from discord import app_commands
from collections import Counter
from utils.fileIO import load_file, save_file
from utils.inventory import has_required_parts, remove_parts
from utils.prestigeBonusHandler import can_craft_tactical, can_craft_explosives

USER_DATA        = "data/user_profiles.json"
RECIPE_DATA      = "data/item_recipes.json"
ARMOR_DATA       = "data/armor_blueprints.json"
EXPLOSIVE_DATA   = "data/explosive_blueprints.json"

# ──────────────────────────────────────────────────────────────────

class CraftDropdown(discord.ui.Select):
    def __init__(self, user_id, options):
        self.user_id = user_id
        super().__init__(
            placeholder="Select a blueprint to craft...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("⚠️ You cannot use someone else's crafting menu.", ephemeral=True)
            return

        item = self.values[0]  # Value is the actual item name (e.g., "Mlock")
        await interaction.response.defer(ephemeral=True)

        user_id = self.user_id
        profiles = await load_file(USER_DATA) or {}
        recipes = await load_file(RECIPE_DATA) or {}
        armor = await load_file(ARMOR_DATA) or {}
        explosives = await load_file(EXPLOSIVE_DATA) or {}

        user = profiles.get(user_id)
        if not user:
            await interaction.followup.send("❌ Profile not found.", ephemeral=True)
            return

        if item not in user.get("blueprints", []):
            await interaction.followup.send(
                f"🔒 You must unlock **{item} Blueprint** before crafting.",
                ephemeral=True
            )
            return

        item_key = item.lower()
        recipe = recipes.get(item_key)
        if not recipe:
            await interaction.followup.send("❌ Unknown item or invalid blueprint selected.", ephemeral=True)
            return

        prestige = user.get("prestige", 0)
        if item_key in armor and not can_craft_tactical(prestige):
            await interaction.followup.send("🔒 Requires Prestige II to craft tactical gear.", ephemeral=True)
            return
        if item_key in explosives and not can_craft_explosives(prestige):
            await interaction.followup.send("🔒 Requires Prestige III to craft explosives or special items.", ephemeral=True)
            return

        stash_counter = Counter(user.get("stash", []))
        if not has_required_parts(stash_counter, recipe["requirements"]):
            missing_parts = [
                f"{qty - stash_counter.get(part, 0)}x {part}"
                for part, qty in recipe["requirements"].items()
                if stash_counter.get(part, 0) < qty
            ]
            await interaction.followup.send(
                "❌ You’re missing the following parts:\n• " + "\n• ".join(missing_parts),
                ephemeral=True
            )
            return

        # ✅ Craft logic
        remove_parts(user["stash"], recipe["requirements"])
        crafted_item = recipe["produces"]
        user["stash"].append(crafted_item)
        user.setdefault("crafted", []).append(crafted_item)
        profiles[user_id] = user
        await save_file(USER_DATA, profiles)

        embed = discord.Embed(
            title="✅ Crafting Successful",
            description=f"You crafted **{crafted_item}**!",
            color=0x2ecc71
        )
        embed.add_field(name="Type",   value=recipe.get("type", "Unknown"), inline=True)
        embed.add_field(name="Rarity", value=recipe.get("rarity", "Common"), inline=True)
        embed.set_footer(text="WARLAB | SV13 Bot")

        await interaction.message.edit(content="", embed=embed, view=None)

# ──────────────────────────────────────────────────────────────────

class CraftView(discord.ui.View):
    def __init__(self, user_id, blueprints):
        super().__init__(timeout=60)
        options = [
            discord.SelectOption(label=f"{bp} Blueprint", value=bp)
            for bp in blueprints[:25]
        ]
        self.add_item(CraftDropdown(user_id, options))

# ──────────────────────────────────────────────────────────────────

class Craft(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="craft", description="Craft an item using your unlocked blueprints")
    async def craft(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        user = profiles.get(user_id)

        if not user:
            await interaction.followup.send("❌ You don’t have a profile yet. Please use `/register` first.", ephemeral=True)
            return

        blueprints = user.get("blueprints", [])
        if not blueprints:
            await interaction.followup.send("🔒 You don’t own any blueprints yet. Use `/blackmarket` to purchase your first one.", ephemeral=True)
            return

        await interaction.followup.send("🛠️ Choose an item to craft:", view=CraftView(user_id, blueprints), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Craft(bot))
