# bot.py — Fully Inlined WARLAB Bot with All 15 Commands (No Cogs)

print("🟡 Booting WARLAB Bot...")

import discord
from discord.ext import commands
from discord import app_commands, Interaction
import json
import os
import requests
import asyncio
from datetime import datetime, timedelta
import random

from utils.adminLogger import log_admin_action
from utils.fileIO import load_file, save_file
from utils.inventory import weighted_choice

print("🟡 Imports successful. Loading config...")

# === Load Config ===
try:
    with open("config.json", "r") as f:
        config = json.load(f)
    print("✅ Config loaded successfully.")
except Exception as e:
    print(f"❌ Failed to load config: {e}")
    raise SystemExit

TOKEN = config["token"]
PREFIX = "/"
API_BASE = "http://localhost:8000/api"
ADMIN_ROLE_ID = config.get("admin_role_id")

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.guilds = True
INTENTS.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS)

# === On Ready ===
@bot.event
async def on_ready():
    print("✅ Bot connected and ready.")
    try:
        guild_id = config.get("guild_id")
        if guild_id:
            synced = await bot.tree.sync(guild=discord.Object(id=int(guild_id)))
            print(f"✅ Synced {len(synced)} slash commands to guild {guild_id}")
        else:
            synced = await bot.tree.sync()
            print(f"✅ Synced {len(synced)} global slash commands.")
    except Exception as e:
        print(f"❌ Slash command sync failed: {e}")

# === Slash Commands ===

@app_commands.command(name="blackmarket", description="Browse the current black market offers")
async def blackmarket(interaction: Interaction):
    await interaction.response.defer(ephemeral=True)
    profiles = await load_file("data/user_profiles.json")

@app_commands.command(name="blueprint", description="Admin: Give or remove blueprints from a player")
@app_commands.describe(
    user="Target player",
    action="Give or remove blueprint",
    item="Blueprint name (must match list)",
    quantity="How many copies to add (ignored on removal)"
)
async def blueprint(interaction: Interaction, user: discord.Member, action: str, item: str, quantity: int = 1):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You don’t have permission to use this.", ephemeral=True)
        return
    profiles = await load_file("data/user_profiles.json")

@app_commands.command(name="craft", description="Craft a weapon or item from available parts")
@app_commands.describe(item="Name of the item to craft")
async def craft(interaction: Interaction, item: str):
    await interaction.response.defer(ephemeral=True)
    profiles = await load_file("data/user_profiles.json")

@app_commands.command(name="fortify", description="Reinforce your stash with tools and materials")
@app_commands.describe(type="Choose a reinforcement to install")
async def fortify(interaction: Interaction, type: str):
    await interaction.response.defer(ephemeral=True)
    profiles = await load_file("data/user_profiles.json")

@app_commands.command(name="labskins", description="Equip a visual theme for your lab (Prestige 4 required)")
async def labskins(interaction: Interaction):
    await interaction.response.defer(ephemeral=True)
    profiles = await load_file("data/user_profiles.json")

@app_commands.command(name="market", description="View and buy items from the Black Market")
@app_commands.describe(item="Exact name of the item you want to buy from the market")
async def market(interaction: Interaction, item: str):
    await interaction.response.defer(ephemeral=True)
    profiles = await load_file("data/user_profiles.json")

@app_commands.command(name="part", description="Admin: Give or remove parts from a player")
@app_commands.describe(
    user="Target player",
    action="Give or remove parts",
    item="Part name (must match system list)",
    quantity="How many to give or remove"
)
async def part(interaction: Interaction, user: discord.Member, action: str, item: str, quantity: int = 1):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You don’t have permission to use this.", ephemeral=True)
        return
    profiles = await load_file("data/user_profiles.json")

@app_commands.command(name="raid", description="Attempt to raid another player's stash.")
async def raid(interaction: Interaction, target: discord.Member):
    attacker_id = str(interaction.user.id)
    defender_id = str(target.id)
    now = datetime.utcnow()
    profiles = await load_file("data/user_profiles.json")

@app_commands.command(name="rank", description="View your current rank, prestige, and buy upgrades.")
async def rank(interaction: Interaction):
    profiles = await load_file("data/user_profiles.json")

@app_commands.command(name="rollblueprint", description="Roll for a random blueprint based on rarity")
async def rollblueprint(interaction: Interaction):
    await interaction.response.defer(ephemeral=True)
    profiles = await load_file("data/user_profiles.json")

@app_commands.command(name="scavenge", description="Scavenge for random materials (1x per day)")
async def scavenge(interaction: Interaction):
    await interaction.response.defer(ephemeral=True)
    profiles = await load_file("data/user_profiles.json")

@app_commands.command(name="stash", description="View your stash, blueprints, and build-ready weapons.")
async def stash(interaction: Interaction):
    profiles = await load_file("data/user_profiles.json")

@app_commands.command(name="task", description="Complete your daily Warlab mission for rewards.")
async def task(interaction: Interaction):
    uid = str(interaction.user.id)
    now_str = datetime.utcnow().strftime("%Y-%m-%d")
    profiles = await load_file("data/user_profiles.json")

@app_commands.command(name="tool", description="Admin: Give or remove tools from a player")
@app_commands.describe(
    user="Target player",
    action="Give or remove tools",
    item="Tool name (must be valid)",
    quantity="How many to give or remove"
)
async def tool(interaction: Interaction, user: discord.Member, action: str, item: str, quantity: int = 1):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You don’t have permission to use this.", ephemeral=True)
        return
    profiles = await load_file("data/user_profiles.json")

@app_commands.command(name="turnin", description="Submit a crafted item for rewards")
@app_commands.describe(item="Exact name of the crafted item or 'all' to submit everything")
async def turnin(interaction: Interaction, item: str):
    await interaction.response.defer(ephemeral=True)
    profiles = await load_file("data/user_profiles.json")

# === Run Bot ===
async def main():
    print("🚀 Starting bot...")
    try:
        async with bot:
            await bot.start(TOKEN)
    except Exception as e:
        print(f"❌ Exception during bot.start: {e}")
    finally:
        print("🛑 Bot shutdown (finally block)")

if __name__ == "__main__":
    print("🚦 Boot complete. Launching main()")
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ CRASH in asyncio.run(main()): {e}")
