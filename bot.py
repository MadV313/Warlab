# bot.py — WARLAB Full Sync Fix

print("🟡 Booting WARLAB Bot...")

import discord
from discord.ext import commands
from discord import Interaction, app_commands
import json
import os
import asyncio
from datetime import datetime

from utils.adminLogger import log_admin_action
from utils.fileIO import load_file, save_file
from utils.inventory import weighted_choice

print("🟡 Imports successful. Loading config...")

# === Load config.json ===
try:
    with open("config.json", "r") as f:
        config = json.load(f)
    print("✅ Config loaded successfully.")
except Exception as e:
    print(f"❌ Failed to load config.json: {e}")
    config = {}

# === Inject Railway env ===
config["token"] = os.getenv("token", config.get("token"))
config["guild_id"] = os.getenv("guild_id", config.get("guild_id"))

if not config.get("token"):
    raise RuntimeError("❌ DISCORD TOKEN MISSING - Set Railway var 'token'")

TOKEN = config["token"]
GUILD_ID = int(config.get("guild_id", "0"))
PREFIX = "/"

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# === On Ready ===
@bot.event
async def on_ready():
    print("✅ Bot connected and ready.")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"✅ Synced {len(synced)} slash commands to guild {GUILD_ID}")
    except Exception as e:
        print(f"❌ Slash sync failed: {e}")


# === Slash Commands ===

@bot.tree.command(name="blackmarket", description="Browse the current black market offers")
async def blackmarket(interaction: Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("📦 Viewing black market...")

@bot.tree.command(name="blueprint", description="Admin: Give or remove blueprints from a player")
@app_commands.describe(user="Target player", action="Give or remove", item="Blueprint name", quantity="How many")
async def blueprint(interaction: Interaction, user: discord.Member, action: str, item: str, quantity: int = 1):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You lack permission.", ephemeral=True)
        return
    await interaction.response.send_message(f"🔧 {action.title()} {quantity}x {item} for {user.display_name}", ephemeral=True)

@bot.tree.command(name="craft", description="Craft a weapon or item")
@app_commands.describe(item="Name of item to craft")
async def craft(interaction: Interaction, item: str):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(f"🔨 Crafting `{item}`...")

@bot.tree.command(name="fortify", description="Reinforce your stash")
@app_commands.describe(type="Choose a reinforcement to install")
async def fortify(interaction: Interaction, type: str):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(f"🛡️ Fortifying with `{type}`...")

@bot.tree.command(name="labskins", description="Equip a visual lab theme (Prestige 4+)")
async def labskins(interaction: Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("🎨 Applying lab skin...")

@bot.tree.command(name="market", description="Buy from the Black Market")
@app_commands.describe(item="Name of the item to buy")
async def market(interaction: Interaction, item: str):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(f"🪙 Buying `{item}` from market...")

@bot.tree.command(name="part", description="Admin: Give or remove parts")
@app_commands.describe(user="Target", action="Give/Remove", item="Part", quantity="Qty")
async def part(interaction: Interaction, user: discord.Member, action: str, item: str, quantity: int = 1):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You lack permission.", ephemeral=True)
        return
    await interaction.response.send_message(f"🔧 {action.title()} {quantity}x `{item}` to {user.display_name}", ephemeral=True)

@bot.tree.command(name="raid", description="Attempt to raid another player's stash")
async def raid(interaction: Interaction, target: discord.Member):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(f"💥 Attempting raid on `{target.display_name}`...")

@bot.tree.command(name="rank", description="View your rank and prestige")
async def rank(interaction: Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("📊 Checking rank...")

@bot.tree.command(name="rollblueprint", description="Roll for a random blueprint")
async def rollblueprint(interaction: Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("🎲 Rolling...")

@bot.tree.command(name="scavenge", description="Scavenge for materials (1x/day)")
async def scavenge(interaction: Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("🧃 Scavenging...")

@bot.tree.command(name="stash", description="View your stash and blueprints")
async def stash(interaction: Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("📦 Opening stash...")

@bot.tree.command(name="task", description="Complete your Warlab mission")
async def task(interaction: Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("📝 Submitting task...")

@bot.tree.command(name="tool", description="Admin: Give or remove tools")
@app_commands.describe(user="Target", action="Give/Remove", item="Tool name", quantity="Qty")
async def tool(interaction: Interaction, user: discord.Member, action: str, item: str, quantity: int = 1):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You lack permission.", ephemeral=True)
        return
    await interaction.response.send_message(f"🛠️ {action.title()} {quantity}x `{item}` to {user.display_name}", ephemeral=True)

@bot.tree.command(name="turnin", description="Submit a crafted item for rewards")
@app_commands.describe(item="Crafted item or 'all'")
async def turnin(interaction: Interaction, item: str):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(f"📤 Turning in `{item}`...")

# === Run Bot ===
async def main():
    print("🚀 Starting bot...")
    try:
        async with bot:
            await bot.start(TOKEN)
    except Exception as e:
        print(f"❌ Exception in bot.start: {e}")
    finally:
        print("🛑 Bot shutdown")

if __name__ == "__main__":
    print("🚦 Launching main()")
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ CRASH in main(): {e}")
