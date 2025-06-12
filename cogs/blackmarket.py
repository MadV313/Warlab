# cogs/blackmarket.py — WARLAB rotating black market shop

import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime

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

class BlackMarket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="blackmarket", description="Browse the current black market offers")
    async def blackmarket(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        user = profiles.get(user_id, {"inventory": [], "prestige": 0})

        # Load or generate market rotation
        market = await load_file(MARKET_FILE)
        if not market or market.get("expires", "") < datetime.utcnow().isoformat():
            market = await self.generate_market()
            await save_file(MARKET_FILE, market)

        offers = market["offers"]
        embed = discord.Embed(title="🛒 WARLAB Black Market", color=0x292b2c)
        embed.set_footer(text="New stock rotates every 24h")

        for item in offers:
            name = item["name"]
            rarity = item["rarity"]
            cost = ITEM_COSTS.get(rarity, 999)
            emoji = RARITY_EMOJIS.get(rarity, "❔")
            embed.add_field(
                name=f"{emoji} {name}",
                value=f"Rarity: **{rarity}**\nCost: **{cost} Prestige**",
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

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
            "expires": datetime.utcnow().isoformat()
        }

async def setup(bot):
    await bot.add_cog(BlackMarket(bot))
