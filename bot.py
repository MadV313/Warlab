# bot.py — WARLAB main launcher

import discord
from discord.ext import commands
import json
import os

# === Load Config ===
with open("config.json", "r") as f:
    config = json.load(f)

TOKEN = config["token"]
PREFIX = "/"

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.guilds = True
INTENTS.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS)

# === Load Cogs ===
@bot.event
async def on_ready():
    print(f"🧪 WARLAB Bot is live as {bot.user}")
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

bot.run(TOKEN)
