# cogs/market.py — WARLAB rotating tools & parts shop (remote coins + buttons + debug)

import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime, timedelta

from utils.fileIO import load_file, save_file

USER_DATA      = "data/user_profiles.json"
MARKET_FILE    = "data/market_rotation.json"
ITEM_POOL_FILE = "data/market_items_master.json"

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

ROTATION_HOURS = 12
ROTATION_DELTA = timedelta(hours=ROTATION_HOURS)

# ──────────────────────────────────────────────────────────────────────────
class BuyButton(discord.ui.Button):
    def __init__(self, label, cost, item_name, category):
        super().__init__(label=f"Buy {label} — {cost}🪙", style=discord.ButtonStyle.green)
        self.item_name = item_name
        self.cost      = cost
        self.category  = category

    async def callback(self, interaction: discord.Interaction):
        user_id  = str(interaction.user.id)
        print(f"🛒 [market.py] Purchase attempt by {user_id} for '{self.item_name}'")

        profiles = await load_file(USER_DATA) or {}
        user     = profiles.get(user_id, {"coins": 0, "stash": []})

        if user.get("coins", 0) < self.cost:
            print(f"❌ [market.py] User {user_id} has insufficient funds ({user.get('coins', 0)} < {self.cost})")
            await interaction.response.send_message("❌ You don’t have enough coins.", ephemeral=True)
            return

        user["coins"] -= self.cost
        user.setdefault("stash", []).append(self.item_name)
        profiles[user_id] = user
        await save_file(USER_DATA, profiles)

        print(f"✅ [market.py] '{self.item_name}' purchased by {user_id}. New balance: {user['coins']} coins")
        await interaction.response.send_message(
            f"✅ You purchased **{self.item_name}**!\n"
            f"💰 New Balance: **{user['coins']} coins**",
            ephemeral=True
        )

# ──────────────────────────────────────────────────────────────────────────
class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="❌ Market closed.", embed=None, view=None)
        print(f"🛑 [market.py] Market view closed by {interaction.user.id}")

# ──────────────────────────────────────────────────────────────────────────
class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="market", description="Browse today’s rotating market")
    async def market(self, interaction: discord.Interaction):
        print(f"📥 [market.py] /market command used by {interaction.user} ({interaction.user.id})")
        await interaction.response.defer(ephemeral=True)

        user_id  = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        user     = profiles.get(user_id)

        if not user:
            print(f"❌ [market.py] No profile found for user {user_id}")
            await interaction.followup.send("❌ You don’t have a profile yet. Please use `/register` first.", ephemeral=True)
            return

        market = await load_file(MARKET_FILE)
        if not market or market.get("expires", "") < datetime.utcnow().isoformat():
            print("🔁 [market.py] Market expired or missing. Generating new rotation...")
            try:
                market = await self.generate_market()
                await save_file(MARKET_FILE, market)
                print("✅ [market.py] New market rotation saved.")
            except Exception as e:
                print(f"❌ [market.py] Market generation failed: {e}")
                await interaction.followup.send(f"❌ Market generation failed: {str(e)}", ephemeral=True)
                return
        else:
            print("🟢 [market.py] Market is still valid. Using current offers.")

        offers = market.get("offers", [])
        if not offers:
            print("⚠️ [market.py] No offers found in market file.")
            await interaction.followup.send("⚠️ No items available in the current market rotation.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🛒 WARLAB Market — Tools & Parts",
            description=f"Your Balance: **{user.get('coins', 0)} coins**",
            color=0x1abc9c
        ).set_footer(text=f"Stock rotates every {ROTATION_HOURS} h")

        view = discord.ui.View(timeout=300)  # 🕒 Extended session timeout here
        for item in offers:
            name     = item["name"]
            category = item["category"]
            cost     = ITEM_COSTS.get(category, 999)
            emoji    = ITEM_EMOJIS.get(category, "❔")

            embed.add_field(
                name=f"{emoji} {name}",
                value=f"Type: **{category.replace('_', ' ').title()}**\nCost: **{cost} coins**",
                inline=False
            )
            view.add_item(BuyButton(name, cost, name, category))

        view.add_item(CloseButton())
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        print(f"✅ [market.py] Market UI sent to user {user_id} with {len(offers)} items")

    # ──────────────────────────────────────────────────────────────────────
    async def generate_market(self):
        full_pool = await load_file(ITEM_POOL_FILE) or {}

        if not isinstance(full_pool, dict):
            raise ValueError("Item pool file is invalid or not structured correctly.")
        print("🎲 [market.py] Generating market from item pool...")

        tools = [name for name, data in full_pool.items()
                 if isinstance(data, dict) and data.get("type") == "tool"]
        parts = [name for name, data in full_pool.items()
                 if isinstance(data, dict) and data.get("type") != "tool"]

        selected_tools = random.sample(tools, k=min(2, len(tools)))
        selected_parts = random.sample(parts, k=min(3, len(parts)))

        offers = []
        for name in selected_tools + selected_parts:
            item_data = full_pool[name]
            offers.append({
                "name": name,
                "category": item_data["type"]
            })

        random.shuffle(offers)
        print(f"📦 [market.py] New rotation: {[o['name'] for o in offers]}")

        return {
            "offers": offers,
            "expires": (datetime.utcnow() + ROTATION_DELTA).isoformat()
        }

# ──────────────────────────────────────────────────────────────────────────
async def setup(bot):
    await bot.add_cog(Market(bot))
