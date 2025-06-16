# cogs/blackmarket.py — WARLAB rotating black market shop (uses coins + buttons)

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
    "Special"  : 250  # ← Guard Dog price
}

RARITY_EMOJIS = {
    "Common"   : "⚪",
    "Uncommon" : "🟢",
    "Rare"     : "🔵",
    "Legendary": "🟣",
    "Special"  : "🐕"
}

# ─────────────────────────────────────────────────────────────────────
class BuyButton(discord.ui.Button):
    def __init__(self, label, cost, item_name, rarity):
        super().__init__(label=f"Buy {label} — {cost}🪙", style=discord.ButtonStyle.green)
        self.item_name = item_name
        self.cost      = cost
        self.rarity    = rarity

    async def callback(self, interaction: discord.Interaction):
        user_id  = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        user     = profiles.get(user_id, {"coins": 0, "inventory": [], "blueprints": []})

        if user.get("coins", 0) < self.cost:
            await interaction.response.send_message("❌ You don’t have enough coins.", ephemeral=True)
            return

        # 💸 Deduct coins
        user["coins"] -= self.cost

        # 📦 Deliver item
        if self.item_name == "Guard Dog":
            user.setdefault("stash", []).append("Guard Dog")
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

# ─────────────────────────────────────────────────────────────────────
class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close", style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        await interaction.message.delete()

# ─────────────────────────────────────────────────────────────────────
class BlackMarket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="blackmarket", description="Browse the current black market offers")
    async def blackmarket(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id  = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        user     = profiles.get(user_id)

        # 🔒 Must be registered
        if not user:
            await interaction.followup.send(
                "❌ You don’t have a profile yet. Please use `/register` first.",
                ephemeral=True
            )
            return

        # Load or (re)generate rotation
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

        view = discord.ui.View()
        for item in offers:
            name   = item["name"]
            rarity = item["rarity"]
            cost   = ITEM_COSTS.get(rarity, 999)
            emoji  = RARITY_EMOJIS.get(rarity, "❔")

            embed.add_field(
                name=f"{emoji} {name}",
                value=f"Rarity: **{rarity}**\nCost: **{cost} coins**",
                inline=False
            )
            view.add_item(BuyButton(name, cost, name, rarity))

        view.add_item(CloseButton())  # ← Add Close button at bottom

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # ─────────────────────────────────────────────────────────────────
    async def generate_market(self):
        all_items = []
        for src in (WEAPONS, ARMOR, EXPLOSIVES):
            pool = await load_file(src)
            for bp in pool.values():
                all_items.append({
                    "name"  : bp["produces"],
                    "rarity": bp.get("rarity", "Common")
                })

        rotation = random.sample(all_items, k=5)

        # 🔒 Ensure Guard Dog is always present
        rotation.append({
            "name"  : "Guard Dog",
            "rarity": "Special"
        })

        return {
            "offers" : rotation,
            "expires": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }

# ─────────────────────────────────────────────────────────────────────
async def setup(bot):
    await bot.add_cog(BlackMarket(bot))
