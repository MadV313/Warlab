# cogs/market.py — WARLAB rotating tools & parts shop (coins + buttons)

import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime, timedelta

from utils.fileIO import load_file, save_file

USER_DATA      = "data/user_profiles.json"

# ── Corrected: daily cache / rotation file =========
MARKET_FILE    = "data/market_rotation.json"          # holds today’s offers + expires

# ── Corrected: master item pool =====================
ITEM_POOL_FILE = "data/market_items_master.json"      # full catalog used to generate offers
# (renamed from ROTATION_FILE → ITEM_POOL_FILE for clarity)

# Flat pricing by simplified type/category
ITEM_COSTS = {
    "tool"       : 50,
    "gun_part"   : 100,
    "armor_part" : 100,
    "mod"        : 150
}

ITEM_EMOJIS = {
    "tool"       : "🛠️",
    "gun_part"   : "🔩",
    "armor_part" : "🛡️",
    "mod"        : "🎯"
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

        await interaction.response.send_message(
            f"✅ You purchased **{self.item_name}**!\n"
            f"💰 New Balance: **{user['coins']} coins**",
            ephemeral=True
        )

# ─────────────────────────────────────────────────────────────────────
class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        await interaction.message.delete()

# ─────────────────────────────────────────────────────────────────────
class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="market", description="Browse today's rotating market")
    async def market(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id  = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        user     = profiles.get(user_id)

        # 🔒 Require profile
        if not user:
            await interaction.followup.send(
                "❌ You don’t have a profile yet. Please use `/register` first.",
                ephemeral=True
            )
            return

        # Load or refresh rotation (3-hour window)
        market = await load_file(MARKET_FILE)
        if not market or market.get("expires", "") < datetime.utcnow().isoformat():
            try:
                market = await self.generate_market()
                await save_file(MARKET_FILE, market)
            except Exception as e:
                await interaction.followup.send(f"❌ Market generation failed: {str(e)}", ephemeral=True)
                return

        offers = market.get("offers", [])
        if not offers:
            await interaction.followup.send("⚠️ No items available in today’s market.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🛒 WARLAB Market — Tools & Parts",
            description=f"Your Balance: **{user.get('coins', 0)} coins**",
            color=0x1abc9c
        ).set_footer(text="Stock rotates every 3 h")

        view = discord.ui.View()
        for item in offers:
            name     = item["name"]
            category = item["category"]
            cost     = ITEM_COSTS.get(category, 999)
            emoji    = ITEM_EMOJIS.get(category, "❔")

            embed.add_field(
                name=f"{emoji} {name}",
                value=f"Type: **{category.title()}**\nCost: **{cost} coins**",
                inline=False
            )
            view.add_item(BuyButton(name, cost, name, category))

        view.add_item(CloseButton())
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # ─────────────────────────────────────────────────────────────────
    async def generate_market(self):
        full_pool = await load_file(ITEM_POOL_FILE) or {}

        if not isinstance(full_pool, dict):
            raise ValueError("Item pool file is invalid or not structured correctly.")

        tools = [name for name, data in full_pool.items()
                 if isinstance(data, dict) and data.get("type") == "tool"]
        parts = [name for name, data in full_pool.items()
                 if isinstance(data, dict) and data.get("type") != "tool"]

        selected_tools = random.sample(tools, k=2) if len(tools) >= 2 else tools
        selected_parts = random.sample(parts, k=3) if len(parts) >= 3 else parts

        offers = []
        for name in selected_tools + selected_parts:
            item_data = full_pool[name]
            offers.append({
                "name": name,
                "category": item_data["type"]
            })

        random.shuffle(offers)

        return {
            "offers": offers,
            "expires": (datetime.utcnow() + timedelta(hours=3)).isoformat()
        }

# ─────────────────────────────────────────────────────────────────────
async def setup(bot):
    await bot.add_cog(Market(bot))
