# bot.py — WARLAB Cog Loader + Reliable Slash Sync + Weekend Boost Announcer

BACKUP_CHANNEL_ID = 1389706195102728322

print("🟡 Booting WARLAB Bot...")

import discord
from discord.ext import commands, tasks
from discord import app_commands
import json, os, asyncio
from datetime import datetime
import pytz

from utils.fileIO import load_file, save_file

# Optional: allow graceful close of shared aiohttp session if present
try:
    from utils import storageClient as _storage_client_mod  # may define SESSION
except Exception:
    _storage_client_mod = None

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
WARLAB_BOT_ID = "1382188850671255612"

# ── Discord bot setup ────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)
bot.config = config
guild_obj = discord.Object(id=GUILD_ID)

# ── Weekend Boost Broadcast ──────────────────────────────────────────────────
boost_announcement_sent = False

@tasks.loop(minutes=180)
async def check_weekend_boosts():
    global boost_announcement_sent
    now = datetime.now(pytz.utc)
    if now.weekday() in [4, 5, 6]:
        if (now.weekday() == 4 and now.hour >= 6) or now.weekday() in [5, 6]:
            if not boost_announcement_sent:
                channel = bot.get_channel(WARLAB_CHANNEL_ID)
                if channel:
                    await channel.send("@everyone <a:bonus:1386436403000512694> **Weekend Boosts are in effect for Scavenge, Tasks, and Raids!**\nLoot and rewards are increased all weekend long — make the most of it!")
                    boost_announcement_sent = True
            return
    boost_announcement_sent = False

# ── Ensure @Warlab is registered ─────────────────────────────────────────────
async def ensure_bot_profile():
    profiles = await load_file("data/user_profiles.json") or {}
    if WARLAB_BOT_ID not in profiles:
        profiles[WARLAB_BOT_ID] = {
            "labskins": ["Rust Bucket"],
            "baseImage": "assets/stash_layers/base_house_prestige1.PNG",
            "reinforcements": {
                "Guard Dog": 1,
                "Claymore Trap": 1,
                "Barbed Fence": 3,
                "Reinforced Gate": 2,
                "Locked Container": 2
            },
            "stash": ["Scrap", "Nails", "Hammer"],
            "coins": 25,
            "prestige_points": 0,
            "raids_successful": 0
        }
        await save_file("data/user_profiles.json", profiles)
        print("✅ Auto-registered @Warlab profile.")

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

    await ensure_bot_profile()

    bot.tree.copy_global_to(guild=guild_obj)
    try:
        synced = await bot.tree.sync(guild=guild_obj)
        print(f"✅ Synced {len(synced)} slash commands to guild {GUILD_ID}")
    except Exception as exc:
        print(f"❌ Slash-sync error: {exc}")

    # Start loops only once to avoid duplicates after reconnects
    if not weekly_backup_loop.is_running():
        weekly_backup_loop.start()
    if not check_weekend_boosts.is_running():
        check_weekend_boosts.start()

@tasks.loop(minutes=60)
async def weekly_backup_loop():
    now = datetime.now(pytz.timezone("US/Eastern"))
    print(f"🕒 [weekly_backup] Tick: {now.strftime('%A %I:%M %p')} EST")

    if now.weekday() == 6 and now.hour == 12:
        print("🗂️ [weekly_backup] Running automatic backup...")

        try:
            profiles = await load_file("data/user_profiles.json") or {}
            os.makedirs("/mnt/data", exist_ok=True)

            backup_path = "/mnt/data/user_profiles_weekly.json"
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(profiles, f, indent=2)

            channel = bot.get_channel(BACKUP_CHANNEL_ID)
            if channel:
                await channel.send(
                    content="🗃️ **Weekly Warlab Backup** — auto-export of `user_profiles.json` at Sunday 12 PM EST",
                    file=discord.File(backup_path)
                )
                print("✅ [weekly_backup] Sent weekly archive to backup channel.")
            else:
                print(f"❌ [weekly_backup] Backup channel ID {BACKUP_CHANNEL_ID} not found.")

        except Exception as e:
            print(f"❌ [weekly_backup] Failed to send backup: {e}")

# ── Log every slash invocation ───────────────────────────────────────────────
@bot.listen("on_interaction")
async def _log(inter):
    if inter.type == discord.InteractionType.application_command:
        print(f"🟢 /{inter.data.get('name')} by {inter.user} ({inter.user.id})")

# ── Run bot ──────────────────────────────────────────────────────────────────
async def main():
    print("🚀 Starting bot…")
    try:
        async with bot:
            await bot.start(TOKEN)
    finally:
        # Graceful shutdown of shared HTTP session (if implemented)
        try:
            if _storage_client_mod and getattr(_storage_client_mod, "SESSION", None):
                if not _storage_client_mod.SESSION.closed:
                    await _storage_client_mod.SESSION.close()
                print("🧹 Closed shared HTTP session.")
        except Exception as e:
            print(f"⚠️ Failed to close shared HTTP session: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as err:
        print(f"💥 Fatal crash: {err}")
