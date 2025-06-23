# cogs/stash.py — Updated with 📦 Crafted Items group for crafted weapons/gear + persistent storage

import discord
from discord.ext import commands
from discord import app_commands
from collections import Counter
from utils.fileIO import load_file

USER_DATA_FILE = "data/user_profiles.json"
ITEMS_MASTER_FILE = "data/items_master.json"
ITEM_RECIPES_FILE = "data/item_recipes.json"
ARMOR_RECIPES_FILE = "data/armor_blueprints.json"
EXPLOSIVE_RECIPES_FILE = "data/explosive_blueprints.json"

TURNIN_ELIGIBLE = [
    "Mlock", "M4", "Mosin", "USG45", "BK-133",
    "Improvised Explosive Device", "Claymore", "Flashbang", "Frag Grenade",
    "Combat Outfit", "Tactical Outfit", "NBC Suit"
]

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

    @app_commands.command(name="stash", description="View your stash, coins, skins, and buildable items.")
    async def stash(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)

        profiles = await load_file(USER_DATA_FILE)
        items_master = await load_file(ITEMS_MASTER_FILE)
        recipes = await load_file(ITEM_RECIPES_FILE)
        armor_recipes = await load_file(ARMOR_RECIPES_FILE)
        explosive_recipes = await load_file(EXPLOSIVE_RECIPES_FILE)

        if not profiles or uid not in profiles:
            await interaction.response.send_message("❌ You don’t have a profile yet. Please use `/register` first.", ephemeral=True)
            return

        user = profiles[uid]
        stash_items = Counter(user.get("stash", []))
        blueprints = user.get("blueprints", [])
        active_skin = user.get("activeSkin", "None")
        coins = user.get("coins", 0)

        all_recipes = {}
        produced_lookup = {}

        for source in (recipes, armor_recipes, explosive_recipes):
            for key, data in source.items():
                all_recipes[key.lower()] = data
                produced = data.get("produces")
                if produced:
                    produced_lookup[produced] = key

        grouped = {
            "🔫 Gun Parts"       : [],
            "🪖 Armor Parts"     : [],
            "💣 Explosives"      : [],
            "🛠️ Tools"          : [],
            "🏚️ Workshop Skins" : [],
            "📦 Crafted Items"   : [],
            "🎒 Misc"            : []
        }

        for item, qty in stash_items.items():
            info = items_master.get(item, {})
            item_type = info.get("type", "").lower()
            label = f"{item} x{qty}"

            is_completed = item in produced_lookup or item in TURNIN_ELIGIBLE

            if is_completed:
                grouped["📦 Crafted Items"].append(label)
            elif item_type == "gun_part":
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
            core_name = blueprint.replace(" Blueprint", "").strip()
            recipe = all_recipes.get(core_name.lower())
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
                value="\n".join(f"• {bp}" for bp in blueprints),
                inline=False
            )

        if buildables:
            embed.add_field(
                name="🧰 Buildable Items",
                value="\n".join(buildables),
                inline=False
            )

        embed.add_field(name="💰 Coins", value=str(coins), inline=True)
        embed.add_field(name="🏚️ Equipped Workshop Skin", value=active_skin, inline=True)

        view = StashView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        sent = await interaction.original_response()
        view.stored_messages = [sent]

async def setup(bot):
    await bot.add_cog(Stash(bot))
