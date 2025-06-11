# bot.py — WARLAB main launcher

import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import requests

# === Load Config ===
with open("config.json", "r") as f:
    config = json.load(f)

TOKEN = config["token"]
PREFIX = "/"
API_BASE = "http://localhost:8000/api"
ADMIN_ROLE_ID = config.get("admin_role_id")

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.guilds = True
INTENTS.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS)

# === API Helper ===
def safe_api_post(endpoint, payload):
    try:
        res = requests.post(f"{API_BASE}/{endpoint}", json=payload)
        if res.status_code != 200:
            return f"❌ API error ({res.status_code})"
        return res.json().get("message", "✅ Success.")
    except Exception as e:
        return f"❌ Failed to contact API: {e}"

# === Inline Slash Commands ===

@bot.tree.command(name="scavenge", description="Scavenge for tools, parts, or coins.")
async def scavenge(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    msg = safe_api_post("scavenge", {"userId": str(interaction.user.id)})
    await interaction.followup.send(msg)

@bot.tree.command(name="craft", description="Craft an item from blueprints and parts.")
@app_commands.describe(item="Name of the item to craft")
async def craft(interaction: discord.Interaction, item: str):
    await interaction.response.defer(thinking=True)
    msg = safe_api_post("craft", {"userId": str(interaction.user.id), "item": item})
    await interaction.followup.send(msg)

@bot.tree.command(name="inventory", description="View your Warlab inventory.")
async def inventory(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    try:
        res = requests.post(f"{API_BASE}/inventory", json={"userId": str(interaction.user.id)})
        data = res.json()
        if "message" in data:
            await interaction.followup.send(data["message"])
            return

        embed = discord.Embed(title=f"{data['username']}'s Inventory", color=0x00ff00)
        embed.add_field(name="🧬 Prestige", value=str(data.get("prestige", 0)))
        embed.add_field(name="💰 Coins", value=str(data.get("coins", 0)))
        embed.add_field(name="🛠️ Tools", value=", ".join(data.get("tools", [])) or "None", inline=False)
        embed.add_field(name="📘 Blueprints", value=", ".join(data.get("blueprints", [])) or "None", inline=False)
        embed.add_field(name="🧩 Crafted", value=", ".join(data.get("crafted", [])) or "None", inline=False)
        parts = data.get("parts", {})
        embed.add_field(name="🔧 Parts", value="\n".join([f"{k} x{v}" for k, v in parts.items()]) or "None", inline=False)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Inventory fetch failed: {e}")

@bot.tree.command(name="turnin", description="Submit a crafted item or 'all' for rewards.")
@app_commands.describe(item="Name of crafted item, or 'all'")
async def turnin(interaction: discord.Interaction, item: str):
    await interaction.response.defer(thinking=True)
    msg = safe_api_post("turnin", {"userId": str(interaction.user.id), "item": item})
    await interaction.followup.send(msg)

@bot.tree.command(name="labskins", description="View or equip unlocked lab skins.")
@app_commands.describe(skin="Optional: skin name to equip")
async def labskins(interaction: discord.Interaction, skin: str = None):
    await interaction.response.defer(thinking=True)
    msg = safe_api_post("labskins", {"userId": str(interaction.user.id), "skin": skin})
    await interaction.followup.send(msg)

# === Admin-Only Commands ===

def is_admin(member):
    return any(role.id == ADMIN_ROLE_ID for role in member.roles)

@bot.tree.command(name="coins", description="(Admin) Give or take coins.")
@app_commands.describe(target="Target user", action="Give or Take", amount="Amount of coins")
async def coins(interaction: discord.Interaction, target: discord.User, action: str, amount: int):
    await interaction.response.defer(ephemeral=True)
    if not is_admin(interaction.user):
        await interaction.followup.send("🚫 You don't have permission.", ephemeral=True)
        return
    msg = safe_api_post("admin/coins", {
        "userId": str(target.id),
        "action": action.lower(),
        "amount": amount
    })
    await interaction.followup.send(msg, ephemeral=True)

@bot.tree.command(name="parts", description="(Admin) Give or take parts.")
@app_commands.describe(target="Target user", action="Give or Take", item="Part name", amount="Quantity")
async def parts(interaction: discord.Interaction, target: discord.User, action: str, item: str, amount: int):
    await interaction.response.defer(ephemeral=True)
    if not is_admin(interaction.user):
        await interaction.followup.send("🚫 You don't have permission.", ephemeral=True)
        return
    msg = safe_api_post("admin/parts", {
        "userId": str(target.id),
        "action": action.lower(),
        "item": item,
        "amount": amount
    })
    await interaction.followup.send(msg, ephemeral=True)

@bot.tree.command(name="blueprint", description="(Admin) Give or take a blueprint.")
@app_commands.describe(target="Target user", action="Give or Take", item="Blueprint name")
async def blueprint(interaction: discord.Interaction, target: discord.User, action: str, item: str):
    await interaction.response.defer(ephemeral=True)
    if not is_admin(interaction.user):
        await interaction.followup.send("🚫 You don't have permission.", ephemeral=True)
        return
    msg = safe_api_post("admin/blueprint", {
        "userId": str(target.id),
        "action": action.lower(),
        "item": item
    })
    await interaction.followup.send(msg, ephemeral=True)

@bot.tree.command(name="labskin_unlock", description="(Admin) Unlock a labskin for a player.")
@app_commands.describe(target="Target user", skin="Name of the skin to unlock")
async def labskin_unlock(interaction: discord.Interaction, target: discord.User, skin: str):
    await interaction.response.defer(ephemeral=True)
    if not is_admin(interaction.user):
        await interaction.followup.send("🚫 You don't have permission.", ephemeral=True)
        return
    try:
        with open("data/user_profiles.json", "r") as f:
            profiles = json.load(f)

        user_id = str(target.id)
        user_data = profiles.get(user_id, {
            "username": target.name,
            "coins": 0,
            "prestige": 0,
            "tools": [],
            "parts": {},
            "blueprints": [],
            "crafted": [],
            "labskins": [],
            "activeSkin": "default",
            "lastScavenge": None
        })

        if skin in user_data.get("labskins", []):
            await interaction.followup.send(f"ℹ️ {target.name} already owns the **{skin}** labskin.", ephemeral=True)
            return

        user_data.setdefault("labskins", []).append(skin)
        profiles[user_id] = user_data

        with open("data/user_profiles.json", "w") as f:
            json.dump(profiles, f, indent=2)

        await interaction.followup.send(f"✅ Unlocked **{skin}** labskin for **{target.name}**!", ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

# === Cog Loader & Slash Sync ===

@bot.event
async def on_ready():
    print(f"🧪 WARLAB Bot is live as {bot.user}")
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            ext = f"cogs.{filename[:-3]}"
            try:
                await bot.load_extension(ext)
                print(f"✅ Loaded cog: {ext}")
            except Exception as e:
                print(f"❌ Failed to load {ext}: {e}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands globally.")
    except Exception as sync_err:
        print(f"❌ Slash command sync failed: {sync_err}")

bot.run(TOKEN)
