# bot.py — WARLAB Cog Loader + Reliable Slash Sync

print("🟡 Booting WARLAB Bot...")

import discord
from discord.ext import commands
from discord import app_commands
import json, os, asyncio
from datetime import datetime

# ── Load config ──────────────────────────────────────────────────────────────
try:
    with open("config.json", "r") as f:
        config = json.load(f)
    print("✅ Config loaded.")
except Exception as e:
    print(f"❌ Failed to load config.json: {e}")
    config = {}

config["token"]   = os.getenv("token",   config.get("token"))
config["guild_id"] = os.getenv("guild_id", config.get("guild_id"))
if not config.get("token"):
    raise RuntimeError("❌ DISCORD TOKEN missing – set Railway var `token`")

TOKEN    = config["token"]
GUILD_ID = int(config.get("guild_id", "0"))
PREFIX   = "/"

# ── Discord bot setup ────────────────────────────────────────────────────────
intents               = discord.Intents.default()
intents.message_content = True
intents.guilds          = True
intents.members         = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)
bot.config = config                          # cogs can access self.bot.config
guild_obj = discord.Object(id=GUILD_ID)      # reuse reference

# ── Auto-load cogs *then* sync commands ──────────────────────────────────────
@bot.event
async def on_ready():
    print("✅ Bot connected.")
    print("🧩 Loading cogs from /cogs…")

    # 1️⃣  Load every cog first
    for fn in os.listdir("./cogs"):
        if fn.endswith(".py") and fn != "__init__.py":
            path = f"cogs.{fn[:-3]}"
            try:
                await bot.load_extension(path)
                print(f"   ✔️  {path}")
            except Exception as exc:
                print(f"   ❌ {path} -> {exc}")

    # 2️⃣  Copy all global commands into the test guild
    bot.tree.copy_global_to(guild=guild_obj)

    # 3️⃣  Sync to guild
    try:
        synced = await bot.tree.sync(guild=guild_obj)
        print(f"✅ Synced {len(synced)} slash commands to guild {GUILD_ID}")
    except Exception as exc:
        print(f"❌ Slash-sync error: {exc}")

# ── Log every slash invocation ───────────────────────────────────────────────
@bot.listen("on_interaction")
async def _log(inter):
    if inter.type == discord.InteractionType.application_command:
        print(f"🟢 /{inter.data.get('name')} by {inter.user} ({inter.user.id})")

# ── Run bot ──────────────────────────────────────────────────────────────────
async def main():
    print("🚀 Starting bot…")
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as err:
        print(f"💥 Fatal crash: {err}")
