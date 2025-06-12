# cogs/stash.py

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

    @app_commands.command(name="stash", description="View your stash, blueprints, and build-ready weapons.")
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

        # Group items
        grouped = {"🛠️ Tools": [], "🔫 Parts": [], "🎯 Mods": [], "🎒 Other": []}
        for item, qty in stash_items.items():
            info = items_master.get(item, {})
            type_ = info.get("type", "").lower()
            label = f"{item} x{qty}"
            if type_ == "tool":
                grouped["🛠️ Tools"].append(label)
            elif "part" in type_:
                grouped["🔫 Parts"].append(label)
            elif type_ == "mod":
                grouped["🎯 Mods"].append(label)
            else:
                grouped["🎒 Other"].append(label)

        # Build-ready check
        buildables = []
        stash_set = Counter(user.get("stash", []))
        for blueprint in blueprints:
            recipe = recipes.get(blueprint.lower())
            if not recipe:
                continue
            requirements = recipe["requirements"]
            can_build = all(stash_set.get(part, 0) >= qty for part, qty in requirements.items())
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

        embed.add_field(name="❄️ Equipped Lab Skin", value=equipped_skin, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Stash(bot))
