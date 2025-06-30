# cogs/blackmarket.py — WARLAB rotating black market shop (remote storage + debug)

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
CAR_PARTS_FILE = "data/car_parts_master.json"  # ✅ NEW

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
    "Special"  : "🪤"
}

class BuyButton(discord.ui.Button):
    def __init__(self, label, cost, item_name, rarity, disabled=False):
        super().__init__(
            label=f"Buy {label} — {cost}🪙",
            style=discord.ButtonStyle.green,
            disabled=disabled
        )
        self.item_name = item_name
        self.cost = cost
        self.rarity = rarity

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        print(f"🛒 [BlackMarket] {interaction.user.name} clicked Buy for: {self.item_name}")
        profiles = await load_file(USER_DATA) or {}
        user = profiles.get(user_id, {"coins": 0, "stash": [], "blueprints": [], "purchasedToday": []})

        if self.item_name in user.get("purchasedToday", []):
            await interaction.response.send_message("❌ You’ve already purchased this item during the current rotation.", ephemeral=True)
            return

        if user.get("coins", 0) < self.cost:
            await interaction.response.send_message("❌ You don’t have enough coins.", ephemeral=True)
            return

        if self.item_name in ["Guard Dog", "Claymore Trap"]:
            user.setdefault("stash", []).append(self.item_name)
        else:
            blueprint_name = f"{self.item_name} Blueprint"
            if blueprint_name in user.get("blueprints", []):
                await interaction.response.send_message("❌ You already own this blueprint.", ephemeral=True)
                return
            user.setdefault("blueprints", []).append(blueprint_name)

        user["coins"] -= self.cost
        user.setdefault("purchasedToday", []).append(self.item_name)

        profiles[user_id] = user
        await save_file(USER_DATA, profiles)
        print(f"💾 [BlackMarket] Purchase saved for {interaction.user.name} — {self.item_name}")

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
            print(f"❌ [BlackMarket] Failed to close UI: {e}")
        await interaction.response.defer()

class MarketView(discord.ui.View):
    def __init__(self, user, offers):
        super().__init__(timeout=300)
        self.stored_messages = []
        owned_blueprints = user.get("blueprints", [])
        purchased = user.get("purchasedToday", [])

        for item in offers:
            name = item["name"]
            rarity = item["rarity"]
            cost = ITEM_COSTS.get(rarity, 999)

            disabled = name in purchased

            if name not in ["Guard Dog", "Claymore Trap"]:
                blueprint_name = f"{name} Blueprint"
                if blueprint_name in owned_blueprints:
                    disabled = True

            self.add_item(BuyButton(name, cost, name, rarity, disabled=disabled))

        self.add_item(CloseButton())

class BlackMarket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="blackmarket", description="Browse the current black market offers")
    async def blackmarket(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        print(f"📡 [BlackMarket] Loading profile for: {interaction.user.name}")
        profiles = await load_file(USER_DATA) or {}
        user = profiles.get(user_id)

        if not user:
            await interaction.followup.send(
                "❌ You don’t have a profile yet. Please use `/register` first.",
                ephemeral=True
            )
            return

        print("📦 [BlackMarket] Checking current rotation...")
        market = await load_file(MARKET_FILE)

        if not market or not isinstance(market, dict) or market.get("expires", "") < datetime.utcnow().isoformat():
            print("🔁 [BlackMarket] Generating new rotation...")
            market = await self.generate_market()
            await save_file(MARKET_FILE, market)

            for uid in profiles:
                profiles[uid]["purchasedToday"] = []
            await save_file(USER_DATA, profiles)
            user = profiles.get(user_id)

        offers = market["offers"]
        car_parts = await load_file(CAR_PARTS_FILE) or []

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

        if car_parts:
            embed.add_field(name="🚗 Humvee Parts", value="Parts required to build the military Humvee:", inline=False)
            for part in car_parts:
                emoji = RARITY_EMOJIS.get(part["rarity"], "🔵")
                cost = ITEM_COSTS.get(part["rarity"], 999)
                embed.add_field(
                    name=f"{emoji} {part['name']}",
                    value=f"Rarity: **{part['rarity']}**\nCost: **{cost} coins**",
                    inline=True
                )

        view = MarketView(user, offers)
        embed_msg = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        view.stored_messages = [embed_msg]

    async def generate_market(self):
        print("🎲 [BlackMarket] Building new item pool from recipes...")
        all_items = []
        for src in (WEAPONS, ARMOR, EXPLOSIVES):
            pool = await load_file(src)
            for bp in pool.values():
                all_items.append({
                    "name": bp["produces"],
                    "rarity": bp.get("rarity", "Common")
                })

        rotation = random.sample(all_items, k=5)
        rotation += [
            {"name": "Guard Dog", "rarity": "Special"},
            {"name": "Claymore Trap", "rarity": "Special"}
        ]

        expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        print(f"📅 [BlackMarket] Rotation expires at: {expires_at}")
        return {
            "offers": rotation,
            "expires": expires_at
        }

async def setup(bot):
    await bot.add_cog(BlackMarket(bot))
