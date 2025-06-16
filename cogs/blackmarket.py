# cogs/blackmarket.py — WARLAB rotating black market shop (uses coins + buttons + fixed Guard Dog + working Close)

import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime, timedelta

from utils.fileIO import load_file, save_file

USER_DATA   = "data/user_profiles.json"
WEAPONS     = "data/item_recipes.json"
ARMOR       = "data/armor_blueprints.json"
EXPLOSIVES  = "data/explosive_blueprints.json"
MARKET_FILE = "data/blackmarket_rotation.json"

ITEM_COSTS = {
    "Common"   : 75,
    "Uncommon" : 150,
    "Rare"     : 300,
    "Legendary": 500,
    "Special"  : 250
}

RARITY_EMOJIS = {
    "Common"   : "⚪",
    "Uncommon" : "🟢",
    "Rare"     : "🔵",
    "Legendary": "🟣",
    "Special"  : "🐕"
}

class BuyButton(discord.ui.Button):
    def __init__(self, label, cost, item_name, rarity):
        super().__init__(label=f"Buy {label} — {cost}🪙", style=discord.ButtonStyle.green)
        self.item_name = item_name
        self.cost = cost
        self.rarity = rarity

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        user = profiles.get(user_id, {"coins": 0, "stash": [], "blueprints": []})

        if user.get("coins", 0) < self.cost:
            await interaction.response.send_message("❌ You don’t have enough coins.", ephemeral=True)
            return

        user["coins"] -= self.cost

        if self.item_name == "Guard Dog":
            user.setdefault("stash", []).append("Guard Dog")  # ✅ Save to stash
        else:
            user.setdefault("blueprints", [])
            if self.item_name not in user["blueprints"]:
                user["blueprints"].append(self.item_name)

        profiles[user_id] = user
        await save_file(USER_DATA, profiles)

        await interaction.response.send_message(
            f"✅ You purchased **{self.item_name}**!\n"
            f"💰 New Balance: **{user['coins']} coins**",
            ephemeral=True
        )

class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close", style=discord.ButtonStyle.danger, row=4)

    async def callback(self, interaction: discord.Interaction):
        try:
            for msg in getattr(self.view, "stored_messages", []):
                await msg.edit(content="❌ Black Market closed.", embed=None, view=None)
        except Exception as e:
            print(f"❌ Failed to close Black Market UI: {e}")
        await interaction.response.defer()

class MarketView(discord.ui.View):
    def __init__(self, user, offers):
        super().__init__(timeout=90)
        self.stored_messages = []
        for item in offers:
            name = item["name"]
            rarity = item["rarity"]
            cost = ITEM_COSTS.get(rarity, 999)
            self.add_item(BuyButton(name, cost, name, rarity))
        self.add_item(CloseButton())

class BlackMarket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="blackmarket", description="Browse the current black market offers")
    async def blackmarket(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        user = profiles.get(user_id)

        if not user:
            await interaction.followup.send(
                "❌ You don’t have a profile yet. Please use `/register` first.",
                ephemeral=True
            )
            return

        market = await load_file(MARKET_FILE)
        if not market or market.get("expires", "") < datetime.utcnow().isoformat():
            market = await self.generate_market()
            await save_file(MARKET_FILE, market)

        offers = market["offers"]

        embed = discord.Embed(
            title="🛒 WARLAB Black Market",
            description=f"Your Balance: **{user.get('coins', 0)} coins**",
            color=0x292b2c
        ).set_footer(text="New stock rotates every 24h")

        for item in offers:
            name = item["name"]
            rarity = item["rarity"]
            emoji = RARITY_EMOJIS.get(rarity, "❔")
            cost = ITEM_COSTS.get(rarity, 999)
            embed.add_field(
                name=f"{emoji} {name}",
                value=f"Rarity: **{rarity}**\nCost: **{cost} coins**",
                inline=False
            )

        view = MarketView(user, offers)
        embed_msg = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        view.stored_messages = [embed_msg]

    async def generate_market(self):
        all_items = []
        for src in (WEAPONS, ARMOR, EXPLOSIVES):
            pool = await load_file(src)
            for bp in pool.values():
                all_items.append({
                    "name": bp["produces"],
                    "rarity": bp.get("rarity", "Common")
                })

        rotation = random.sample(all_items, k=5)
        rotation.append({
            "name": "Guard Dog",
            "rarity": "Special"
        })

        return {
            "offers": rotation,
            "expires": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }

async def setup(bot):
    await bot.add_cog(BlackMarket(bot))
