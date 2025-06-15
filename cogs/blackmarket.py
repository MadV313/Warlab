# cogs/blackmarket.py — WARLAB rotating black market shop (uses coins + buttons)

import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime, timedelta

from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
WEAPONS = "data/item_recipes.json"
ARMOR = "data/armor_blueprints.json"
EXPLOSIVES = "data/explosive_blueprints.json"
MARKET_FILE = "data/blackmarket_rotation.json"

ITEM_COSTS = {
    "Common": 30,
    "Uncommon": 75,
    "Rare": 150,
    "Legendary": 300
}

RARITY_EMOJIS = {
    "Common": "⚪",
    "Uncommon": "🟢",
    "Rare": "🔵",
    "Legendary": "🟣"
}


class BuyButton(discord.ui.Button):
    def __init__(self, label, cost, item_name):
        super().__init__(label=f"Buy {label} — {cost}🪙", style=discord.ButtonStyle.green)
        self.item_name = item_name
        self.cost = cost

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        user = profiles.get(user_id, {"coins": 0, "blueprints": []})

        if user["coins"] < self.cost:
            await interaction.response.send_message("❌ You don’t have enough coins.", ephemeral=True)
            return

        user["coins"] -= self.cost
        user.setdefault("blueprints", [])
        if self.item_name not in user["blueprints"]:
            user["blueprints"].append(self.item_name)

        profiles[user_id] = user
        await save_file(USER_DATA, profiles)
        await interaction.response.send_message(f"✅ You purchased **{self.item_name}**!", ephemeral=True)


class BlackMarket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="blackmarket", description="Browse the current black market offers")
    async def blackmarket(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        user = profiles.get(user_id, {"inventory": [], "coins": 0})

        # Load or generate market rotation
        market = await load_file(MARKET_FILE)
        if not market or market.get("expires", "") < datetime.utcnow().isoformat():
            market = await self.generate_market()
            await save_file(MARKET_FILE, market)

        offers = market["offers"]
        embed = discord.Embed(
            title="🛒 WARLAB Black Market",
            description=f"Your Balance: **{user.get('coins', 0)} coins**",
            color=0x292b2c
        )
        embed.set_footer(text="New stock rotates every 24h")

        view = discord.ui.View()
        for item in offers:
            name = item["name"]
            rarity = item["rarity"]
            cost = ITEM_COSTS.get(rarity, 999)
            emoji = RARITY_EMOJIS.get(rarity, "❔")

            embed.add_field(
                name=f"{emoji} {name}",
                value=f"Rarity: **{rarity}**\nCost: **{cost} coins**",
                inline=False
            )
            view.add_item(BuyButton(name, cost, name))

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def generate_market(self):
        all_items = []
        for src in [WEAPONS, ARMOR, EXPLOSIVES]:
            pool = await load_file(src)
            for bp in pool.values():
                all_items.append({
                    "name": bp["produces"],
                    "rarity": bp.get("rarity", "Common")
                })

        selected = random.sample(all_items, k=5)
        return {
            "offers": selected,
            "expires": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }


async def setup(bot):
    await bot.add_cog(BlackMarket(bot))
