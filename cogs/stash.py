# cogs/stash.py — Expanded stash viewer with close button from Black Market

import discord
from discord.ext import commands
from discord import app_commands
import json
from collections import Counter

USER_DATA_FILE = "data/user_profiles.json"
ITEMS_MASTER_FILE = "data/items_master.json"
ITEM_RECIPES_FILE = "data/item_recipes.json"

# 🔴 Close Button (copied from Black Market)
class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close", style=discord.ButtonStyle.danger, row=4)

    async def callback(self, interaction: discord.Interaction):
        try:
            for msg in getattr(self.view, "stored_messages", []):
                await msg.edit(content="❌ Stash view closed.", embed=None, view=None)
        except Exception as e:
            print(f"❌ Failed to close stash UI: {e}")
        await interaction.response.defer()

class StashView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=90)
        self.stored_messages = []
        self.add_item(CloseButton())

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
            await interaction.response.send_message("❌ You don’t have a profile yet. Please use `/register` first.", ephemeral=True)
            return

        stash_items = Counter(user.get("stash", []))
        blueprints = user.get("blueprints", [])
        equipped_skin = user.get("equipped_skin", "None")
        coins = user.get("coins", 0)

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
            item_type = info.get("type", "").lower()
            label = f"{item} x{qty}"

            if item_type == "gun_part":
                grouped["🔫 Gun Parts"].append(label)
            elif item_type == "armor_part":
                grouped["🪖 Armor Parts"].append(label)
            elif item_type == "explosive_part":
                grouped["💣 Explosives"].append(label)
            elif item_type == "tool":
                grouped["🛠️ Tools"].append(label)
            elif item_type == "skin":
                grouped["🏚️ Workshop Skins"].append(label)
            else:
                grouped["🎒 Misc"].append(label)

        buildables = []
        for blueprint in blueprints:
            recipe = recipes.get(blueprint.lower())
            if not recipe:
                continue
            requirements = recipe.get("requirements", {})
            can_build = all(stash_items.get(part, 0) >= qty for part, qty in requirements.items())
            status = "✅ Build Ready" if can_build else "❌ Missing Parts"
            buildables.append(f"{recipe['produces']} — {status}")

        embed = discord.Embed(
            title=f"🎒 {interaction.user.display_name}'s Stash",
            color=0x74c1f2
        )

        for group, items in grouped.items():
            if items:
                embed.add_field(name=group, value="\n".join(items), inline=False)

        if blueprints:
            embed.add_field(
                name="📘 Blueprints Owned",
                value="\n".join([f"• {bp}" for bp in blueprints]),
                inline=False
            )

        if buildables:
            embed.add_field(
                name="🧰 Buildable Weapons",
                value="\n".join(buildables),
                inline=False
            )

        embed.add_field(name="💰 Coins", value=str(coins), inline=True)
        embed.add_field(name="🏚️ Equipped Workshop Skin", value=equipped_skin, inline=True)

        view = StashView()
        msg = await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        sent = await interaction.original_response()
        view.stored_messages = [sent]

async def setup(bot):
    await bot.add_cog(Stash(bot))
