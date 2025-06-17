# cogs/task.py — Daily Warlab mission with crafted item highlights

import discord
from discord.ext import commands
from discord import app_commands
import json, random
from datetime import datetime

from utils.boosts import is_weekend_boost_active  # ✅ Boost helper

USER_DATA_FILE       = "data/user_profiles.json"
ITEMS_MASTER_FILE    = "data/items_master.json"
BLACKMARKET_FILE     = "data/blackmarket_items_master.json"
RECIPE_PATHS         = [
    "data/item_recipes.json",
    "data/armor_blueprints.json",
    "data/explosive_blueprints.json"
]
EMOJI_35 = "<a:emoji_35:1372056026840305757>"

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
    f"Assisted ᑲ୧𐒐𝘤Ꚕ 🝃𝜕ᒋᗰ୧ᒋઽ {EMOJI_35} operatives during a covert exchange near Gieraltów fields.",
    f"Delivered encrypted cargo for ᑲ୧𐒐𝘤Ꚕ 🝃𝜕ᒋᗰ୧ᒋઽ {EMOJI_35} agents hiding near the abandoned Roslavl factory."
]

TOOL_POOL = ["Pliers", "Saw", "Nails", "Hammer"]

class Task(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    def _load_all_crafted_items(self):
        crafted = set()
        for path in RECIPE_PATHS:
            data = self._load(path)
            for entry in data.values():
                output = entry.get("produces")
                if output:
                    crafted.add(output)
        return crafted

    @app_commands.command(name="task", description="Complete your daily Warlab mission for rewards.")
    async def task(self, interaction: discord.Interaction):
        uid       = str(interaction.user.id)
        profiles  = self._load(USER_DATA_FILE)
        today_str = datetime.utcnow().strftime("%Y-%m-%d")

        user = profiles.get(uid)
        if not user:
            await interaction.response.send_message("❌ You don’t have a profile yet. Please use `/register` first.", ephemeral=True)
            return

        if user.get("last_task") == today_str:
            await interaction.response.send_message("🕒 You’ve already completed your daily task. Try again tomorrow.", ephemeral=True)
            return

        items_master = self._load(ITEMS_MASTER_FILE)
        black_market = self._load(BLACKMARKET_FILE)
        crafted_set  = self._load_all_crafted_items()

        std_pool  = list(items_master.keys())
        rare_pool = list(black_market.keys())

        base_coins = random.randint(40, 80)
        if user.get("boosts", {}).get("coin_doubler"):
            base_coins *= 2
        user["coins"] = user.get("coins", 0) + base_coins
        user["last_task"] = today_str

        bonus_rolls = 0
        boosts      = user.get("boosts", {})

        if boosts.get("perm_loot_boost"):
            bonus_rolls += 1
        if boosts.get("daily_loot_boost") and user.get("daily_task_loot_used") != today_str:
            bonus_rolls += 1
            user["daily_task_loot_used"] = today_str
        if is_weekend_boost_active():
            bonus_rolls += 1

        total_rolls = 1 + bonus_rolls
        guaranteed_tool = random.choice(TOOL_POOL)
        item_rewards = [guaranteed_tool]
        crafted_rewards = []

        user.setdefault("stash", []).append(guaranteed_tool)

        for _ in range(total_rolls):
            is_rare = random.randint(1, 100) <= 5
            loot    = random.choice(rare_pool) if (is_rare and rare_pool) else random.choice(std_pool)
            item_rewards.append(loot)
            user["stash"].append(loot)
            if loot in crafted_set:
                crafted_rewards.append(loot)

        profiles[uid] = user
        self._save(USER_DATA_FILE, profiles)

        mission = random.choice(DAILY_TASKS)
        embed = discord.Embed(title="📋 Daily Task Complete!", color=0x8DE68A)
        embed.add_field(name="🧪 Mission",       value=mission,            inline=False)
        embed.add_field(name="💰 Coins Earned",  value=f"{base_coins}",    inline=True)
        embed.add_field(
            name="📦 Items Gained",
            value="\n".join([f"{'🧰' if itm in crafted_set else '🔧'} {itm}" for itm in item_rewards]),
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

        # 🔔 Bonus crafted item follow-up
        if crafted_rewards:
            crafted_line = ", ".join([f"**{itm}**" for itm in crafted_rewards])
            await interaction.followup.send(
                f"🚨 Turn-in ready item pulled! Use `/turnin` to redeem: {crafted_line}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Task(bot))
