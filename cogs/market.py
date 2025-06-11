# cogs/market.py — WARLAB market browse + purchase command

import discord
from discord.ext import commands
from discord import app_commands

from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
MARKET_FILE = "data/blackmarket_rotation.json"
UNLOCKED_BP_FILE = "data/unlocked_blueprints.json"

ITEM_COSTS = {
    "Common": 30,
    "Uncommon": 75,
    "Rare": 150,
    "Legendary": 300
}

class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="market", description="View and buy items from the Black Market")
    @app_commands.describe(item="Exact name of the item you want to buy from the market")
    async def market(self, interaction: discord.Interaction, item: str):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        user_data = await load_file(USER_DATA) or {}
        bp_data = await load_file(UNLOCKED_BP_FILE) or {}
        market = await load_file(MARKET_FILE) or {}

        user = user_data.get(user_id, {"inventory": [], "prestige": 0})
        unlocked = bp_data.get(user_id, [])

        offers = market.get("offers", [])
        item_entry = next((o for o in offers if o["name"].lower() == item.lower()), None)

        if not item_entry:
            await interaction.followup.send("❌ That item is not currently available in the market.", ephemeral=True)
            return

        rarity = item_entry["rarity"]
        cost = ITEM_COSTS.get(rarity, 999)
        if user["prestige"] < cost:
            await interaction.followup.send(f"❌ You need {cost} Prestige to buy this item. You only have {user['prestige']}.", ephemeral=True)
            return

        # Deduct cost and unlock blueprint
        user["prestige"] -= cost
        if item_entry["name"] not in unlocked:
            unlocked.append(item_entry["name"])
            msg = f"✅ You bought **{item_entry['name']}** and unlocked the blueprint!"
        else:
            msg = f"✅ You bought **{item_entry['name']}**, but you already own this blueprint."

        user_data[user_id] = user
        bp_data[user_id] = unlocked

        await save_file(USER_DATA, user_data)
        await save_file(UNLOCKED_BP_FILE, bp_data)

        await interaction.followup.send(msg, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Market(bot))
