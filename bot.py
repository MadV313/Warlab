# bot.py — WARLAB Cog Loader + Full Sync + Debug Logging

print("🟡 Booting WARLAB Bot...")

import discord
from discord.ext import commands
from discord import Interaction, app_commands
import json
import os
import asyncio
from datetime import datetime

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

# ✅ Inject config into bot instance for cog access
bot.config = config

# === Auto-load cogs from /cogs ===
@bot.event
async def setup_hook():
    print("🧩 Loading cogs from /cogs...")
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
            cog_path = f"cogs.{filename[:-3]}"
            try:
                await bot.load_extension(cog_path)
                print(f"✅ Loaded cog: {cog_path}")
            except Exception as e:
                print(f"❌ Failed to load {cog_path}: {e}")

# === Sync Slash Commands on Ready ===
@bot.event
async def on_ready():
    print("✅ Bot connected and ready.")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"✅ Synced {len(synced)} slash commands to guild {GUILD_ID}")
    except Exception as e:
        print(f"❌ Slash sync failed: {e}")

# === Log Slash Command Usage ===
@bot.listen("on_interaction")
async def log_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.application_command:
        name = interaction.data.get("name")
        user = interaction.user
        print(f"🟢 /{name} by {user.display_name} ({user.id})")

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
