# cogs/stash.py — Expanded stash viewer with parts, coins, lab skins

import discord
from discord.ext import commands
from discord import app_commands
import json
from collections import Counter

USER_DATA_FILE = "data/user_profiles.json"
ITEMS_MASTER_FILE = "data/items_master.json"
ITEM_RECIPES_FILE = "data/item_recipes.json"

class Stash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_json(self, path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            return {}

    @app_commands.command(name="stash", description="View your stash, coins, skins, and buildable items.")
    async def stash(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        profiles = self.load_json(USER_DATA_FILE)
        items_master = self.load_json(ITEMS_MASTER_FILE)
        recipes = self.load_json(ITEM_RECIPES_FILE)

        user = profiles.get(uid)
        if not user:
            await interaction.response.send_message("❌ You don’t have a profile yet.", ephemeral=True)
            return

        stash_items = Counter(user.get("stash", []))
        blueprints = user.get("blueprints", [])
        equipped_skin = user.get("equipped_skin", "None")
        coins = user.get("coins", 0)

        # Group stash by tag logic
        grouped = {
            "🔫 Gun Parts": [],
            "🪖 Armor Parts": [],
            "💣 Explosives": [],
            "🛠️ Tools": [],
            "🏚️ Workshop Skins": [],
            "🎒 Misc": []
        }

        for item, qty in stash_items.items():
            info = items_master.get(item, {})
            tags = info.get("tags", [])
            label = f"{item} x{qty}"

            if "gun_part" in tags:
                grouped["🔫 Gun Parts"].append(label)
            elif "armor_part" in tags:
                grouped["🪖 Armor Parts"].append(label)
            elif "explosive_part" in tags:
                grouped["💣 Explosives"].append(label)
            elif "tool" in tags:
                grouped["🛠️ Tools"].append(label)
            elif "skin" in tags:
                grouped["🏚️ Workshop Skins"].append(label)
            else:
                grouped["🎒 Misc"].append(label)

        # Check for build-ready weapons
        buildables = []
        for blueprint in blueprints:
            recipe = recipes.get(blueprint.lower())
            if not recipe:
                continue
            requirements = recipe.get("requirements", {})
            can_build = all(stash_items.get(part, 0) >= qty for part, qty in requirements.items())
            status = "✅ Build Ready" if can_build else "❌ Missing Parts"
            buildables.append(f"{recipe['produces']} — {status}")

        # Build embed
        embed = discord.Embed(title=f"🎒 {interaction.user.display_name}'s Stash", color=0x74c1f2)

        for group, items in grouped.items():
            if items:
                embed.add_field(name=group, value="\n".join(items), inline=False)

        if blueprints:
            embed.add_field(name="📘 Blueprints Owned", value="\n".join([f"• {bp}" for bp in blueprints]), inline=False)

        if buildables:
            embed.add_field(name="🧰 Buildable Weapons", value="\n".join(buildables), inline=False)

        embed.add_field(name="💰 Coins", value=str(coins), inline=True)
        embed.add_field(name="🏚️ Equipped Workshop Skin", value=equipped_skin, inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Stash(bot))
