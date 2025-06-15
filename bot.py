# bot.py — WARLAB Cog Loader + Reliable Slash Sync + Weekend Boost Announcer

print("🟡 Booting WARLAB Bot...")

import discord
from discord.ext import commands, tasks
from discord import app_commands
import json, os, asyncio
from datetime import datetime
import pytz

# ── Load config ──────────────────────────────────────────────────────────────
try:
    with open("config.json", "r") as f:
        config = json.load(f)
    print("✅ Config loaded.")
except Exception as e:
    print(f"❌ Failed to load config.json: {e}")
    config = {}

config["token"]    = os.getenv("token", config.get("token"))
config["guild_id"] = os.getenv("guild_id", config.get("guild_id"))
if not config.get("token"):
    raise RuntimeError("❌ DISCORD TOKEN missing – set Railway var `token`")

TOKEN     = config["token"]
GUILD_ID  = int(config.get("guild_id", "0"))
PREFIX    = "/"
WARLAB_CHANNEL_ID = 1382187883590455296

# ── Discord bot setup ────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)
bot.config = config                          # cogs can access self.bot.config
guild_obj = discord.Object(id=GUILD_ID)      # reuse reference

# ── Weekend Boost Broadcast ──────────────────────────────────────────────────
boost_announcement_sent = False

@tasks.loop(minutes=180)
async def check_weekend_boosts():
    global boost_announcement_sent
    now = datetime.now(pytz.utc)

    # Friday 6AM UTC through Sunday 11:59PM UTC
    if now.weekday() in [4, 5, 6]:
        if (now.weekday() == 4 and now.hour >= 6) or now.weekday() in [5, 6]:
            if not boost_announcement_sent:
                channel = bot.get_channel(WARLAB_CHANNEL_ID)
                if channel:
                    await channel.send("@everyone 🔥 **Weekend Boosts are in effect for Scavenge, Tasks, and Raids!**\nLoot and rewards are increased all weekend long — make the most of it!")
                    boost_announcement_sent = True
            return

    # Reset flag when boost ends (Monday)
    boost_announcement_sent = False

# ── Auto-load cogs *then* sync commands ──────────────────────────────────────
@bot.event
async def on_ready():
    print("✅ Bot connected.")
    print("🧩 Loading cogs from /cogs…")

    for fn in os.listdir("./cogs"):
        if fn.endswith(".py") and fn != "__init__.py":
            path = f"cogs.{fn[:-3]}"
            try:
                await bot.load_extension(path)
                print(f"   ✔️  {path}")
            except Exception as exc:
                print(f"   ❌ {path} -> {exc}")

    bot.tree.copy_global_to(guild=guild_obj)
    try:
        synced = await bot.tree.sync(guild=guild_obj)
        print(f"✅ Synced {len(synced)} slash commands to guild {GUILD_ID}")
    except Exception as exc:
        print(f"❌ Slash-sync error: {exc}")

    check_weekend_boosts.start()  # ⏱ Start weekend boost checker

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
