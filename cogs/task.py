# cogs/task.py — Daily Warlab mission with new boost logic

import discord
from discord.ext import commands
from discord import app_commands
import json, random
from datetime import datetime

from utils.boosts import is_weekend_boost_active  # ✅ NEW boost helper

USER_DATA_FILE       = "data/user_profiles.json"
ITEMS_MASTER_FILE    = "data/items_master.json"
BLACKMARKET_FILE     = "data/blackmarket_items_master.json"

DAILY_TASKS = [
    "Cleared an infected nest outside Topolin.",
    "Assisted a wounded survivor near Sobotka Trader.",
    "Eliminated a roaming bandit squad near Sitnik Airfield.",
    "Neutralized a rogue marksman spotted near Polana treeline.",
    "Intercepted a smuggler convoy north of the Zalesie checkpoint.",
    "Helped reinforce survivor barricades outside Brena village.",
    "Salvaged black market tech hidden beneath a barn near Kolin.",
    "Braved a toxic gas pocket near Kamensk Quarry to extract intel.",
    "Navigated a thunderstorm sweep across the Livonia river delta to tag airdrop wreckage.",
    "Assisted ᑲ୧𐒐𝘤Ꚕ 🝃𝜕ᒋᗰ୧ᒋઽ <a:emoji_35:1372056026840305757> operatives during a covert exchange near Gieraltów fields.",
    "Delivered encrypted cargo for ᑲ୧𐒐𝘤Ꚕ 🝃𝜕ᒋᗰ୧ᒋઽ <a:emoji_35:1372056026840305757> agents hiding near the abandoned Roslavl factory."
]

TOOL_POOL = ["Pliers", "Saw", "Nails", "Hammer"]  # guaranteed-tool list

class Task(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ───────────────────────── helpers ──────────────────────────
    @staticmethod
    def _load(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            return {}

    @staticmethod
    def _save(path, data):
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    # ───────────────────────── command ──────────────────────────
    @app_commands.command(name="task", description="Complete your daily Warlab mission for rewards.")
    async def task(self, interaction: discord.Interaction):
        uid       = str(interaction.user.id)
        profiles  = self._load(USER_DATA_FILE)
        today_str = datetime.utcnow().strftime("%Y-%m-%d")

        # ❌ Registration check (safe)
        user = profiles.get(uid)
        if not user:
            await interaction.response.send_message(
                "❌ You don’t have a profile yet. Please use `/register` first.",
                ephemeral=True
            )
            return

        if user.get("last_task") == today_str:
            await interaction.response.send_message(
                "🕒 You’ve already completed your daily task. Try again tomorrow.",
                ephemeral=True
            )
            return

        # ── Load loot pools ─────────────────────────────────────
        items_master = self._load(ITEMS_MASTER_FILE)
        black_market = self._load(BLACKMARKET_FILE)

        std_pool  = list(items_master.keys())
        rare_pool = list(black_market.keys())

        # ── Coin reward (with doubler) ──────────────────────────
        base_coins = random.randint(40, 80)
        if user.get("boosts", {}).get("coin_doubler"):
            base_coins *= 2
        user["coins"] = user.get("coins", 0) + base_coins
        user["last_task"] = today_str

        # ── Determine how many bonus rolls ──────────────────────
        bonus_rolls = 0
        boosts      = user.get("boosts", {})

        if boosts.get("perm_loot_boost"):
            bonus_rolls += 1

        if boosts.get("daily_loot_boost") and user.get("daily_task_loot_used") != today_str:
            bonus_rolls += 1
            user["daily_task_loot_used"] = today_str  # stamp usage

        if is_weekend_boost_active():
            bonus_rolls += 1

        # always 1 extra roll by default
        total_rolls = 1 + bonus_rolls

        # ── Guaranteed tool ─────────────────────────────────────
        guaranteed_tool = random.choice(TOOL_POOL)
        item_rewards    = [guaranteed_tool]
        user.setdefault("stash", []).append(guaranteed_tool)

        # ── Random loot rolls ───────────────────────────────────
        for _ in range(total_rolls):
            is_rare = random.randint(1, 100) <= 5
            loot    = random.choice(rare_pool) if (is_rare and rare_pool) else random.choice(std_pool)
            item_rewards.append(loot)
            user["stash"].append(loot)

        # ── Persist profile ─────────────────────────────────────
        profiles[uid] = user
        self._save(USER_DATA_FILE, profiles)

        # ── Build embed ─────────────────────────────────────────
        mission = random.choice(DAILY_TASKS)
        embed   = discord.Embed(title="📋 Daily Task Complete!", color=0x8DE68A)
        embed.add_field(name="🧪 Mission",       value=mission,            inline=False)
        embed.add_field(name="💰 Coins Earned",  value=f"{base_coins}",    inline=True)
        embed.add_field(
            name="📦 Items Gained",
            value="\n".join([f"🔧 {itm}" for itm in item_rewards]),
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Task(bot))
