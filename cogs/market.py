# cogs/market.py — WARLAB rotating tools & parts shop (coins + buttons)

import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime, timedelta

from utils.fileIO import load_file, save_file

USER_DATA      = "data/user_profiles.json"
MARKET_FILE    = "data/market_rotation.json"

# Hard-coded pools  ▸ expand / load from JSON later if desired
TOOL_POOL  = ["Hammer", "Pliers", "Saw", "Wrench", "Screwdriver", "Drill"]
PART_POOL  = ["Gun Barrel", "Gun Stock", "Trigger Assembly",
              "Kevlar Plate", "Ballistic Fabric", "Ceramic Insert"]

# Cost table (simple flat pricing)
ITEM_COSTS = {
    "Tool" : 50,
    "Part" : 40
}

# Simple emoji tags
ITEM_EMOJIS = {
    "Tool" : "🛠️",
    "Part" : "🔩"
}

# ─────────────────────────────────────────────────────────────────────
class BuyButton(discord.ui.Button):
    def __init__(self, label, cost, item_name, category):
        super().__init__(label=f"Buy {label} — {cost}🪙", style=discord.ButtonStyle.green)
        self.item_name = item_name
        self.cost      = cost
        self.category  = category

    async def callback(self, interaction: discord.Interaction):
        user_id  = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        user     = profiles.get(user_id, {"coins": 0, "inventory": []})

        if user.get("coins", 0) < self.cost:
            await interaction.response.send_message("❌ You don’t have enough coins.", ephemeral=True)
            return

        # 💸 Deduct coins & deliver item
        user["coins"] -= self.cost
        user.setdefault("inventory", []).append(self.item_name)

        profiles[user_id] = user
        await save_file(USER_DATA, profiles)
        await interaction.response.send_message(f"✅ You purchased **{self.item_name}**!", ephemeral=True)

# ─────────────────────────────────────────────────────────────────────
class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Main command (no argument)
    @app_commands.command(name="market", description="Browse today's Tools & Parts market")
    async def market(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id  = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        user     = profiles.get(user_id, {"coins": 0})

        # Load or refresh rotation (3-hour window)
        market = await load_file(MARKET_FILE)
        if not market or market.get("expires", "") < datetime.utcnow().isoformat():
            market = await self.generate_market()
            await save_file(MARKET_FILE, market)

        offers = market["offers"]

        embed = discord.Embed(
            title="🛒 WARLAB Market — Tools & Parts",
            description=f"Your Balance: **{user.get('coins', 0)} coins**",
            color=0x1abc9c
        ).set_footer(text="Stock rotates every 3 h")

        view = discord.ui.View()
        for item in offers:
            name      = item["name"]
            category  = item["category"]
            cost      = ITEM_COSTS[category]
            emoji     = ITEM_EMOJIS[category]

            embed.add_field(
                name=f"{emoji} {name}",
                value=f"Category: **{category}**\nCost: **{cost} coins**",
                inline=False
            )
            view.add_item(BuyButton(name, cost, name, category))

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # ─────────────────────────────────────────────────────────────────
    async def generate_market(self):
        # Always 2 tools
        tools = random.sample(TOOL_POOL, k=2)
        # And 3 parts
        parts = random.sample(PART_POOL, k=3)

        rotation = (
            [{"name": t, "category": "Tool"} for t in tools] +
            [{"name": p, "category": "Part"} for p in parts]
        )
        random.shuffle(rotation)

        return {
            "offers" : rotation,
            "expires": (datetime.utcnow() + timedelta(hours=3)).isoformat()
        }

# ─────────────────────────────────────────────────────────────────────
async def setup(bot):
    await bot.add_cog(Market(bot))
