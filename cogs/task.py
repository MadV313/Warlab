# cogs/task.py

import discord
from discord.ext import commands
from discord import app_commands
import json
import random
from datetime import datetime

USER_DATA_FILE = "data/user_profiles.json"
ITEMS_MASTER_FILE = "data/items_master.json"
BLACKMARKET_FILE = "data/blackmarket_items_master.json"

DAILY_TASKS = [
    "Cleared an infected nest outside Topolin.",
    "Scavenged rare parts from a downed chopper.",
    "Assisted a wounded survivor near Sobotka Trader.",
    "Eliminated a roaming bandit squad near Sitnik Airfield.",
    "Recovered a hidden weapons cache west of Nadbor.",
    "Neutralized a rogue marksman spotted near Polana treeline.",
    "Secured medical supplies from an overrun clinic in Tarnow.",
    "Intercepted a smuggler convoy north of the Zalesie checkpoint.",
    "Helped reinforce survivor barricades outside Brena village.",
    "Salvaged black market tech hidden beneath a barn near Kolin.",
    "Braved a toxic gas pocket near Kamensk Quarry to extract intel.",
    "Navigated a thunderstorm sweep across the Livonia river delta to tag airdrop wreckage.",
    "Harvested mutated crops from a contaminated greenhouse in Branzow.",
    "Assisted ᑲ୧𐒐𝘤Ꚕ 🝃𝜕ᒋᗰ୧ᒋઽ <a:emoji_35:1372056026840305757> operatives during a covert exchange near Gieraltów fields.",
    "Delivered encrypted cargo for ᑲ୧𐒐𝘤Ꚕ 🝃𝜕ᒋᗰ୧ᒋઽ <a:emoji_35:1372056026840305757> agents hiding near the abandoned Roslavl factory."
]

TOOL_POOL = ["Pliers", "Saw", "Nails", "Hammer"]

class Task(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_json(self, path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            return {}

    def save_profiles(self, data):
        with open(USER_DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)

    @app_commands.command(name="task", description="Complete your daily Warlab mission for rewards.")
    async def task(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        profiles = self.load_json(USER_DATA_FILE)
        now_str = datetime.utcnow().strftime("%Y-%m-%d")

        user = profiles.get(uid)
        if not user:
            await interaction.response.send_message("❌ You don’t have a profile yet. Use `/rank` or `/turnin` to get started.", ephemeral=True)
            return

        if user.get("last_task") == now_str:
            await interaction.response.send_message("🕒 You’ve already completed your daily task. Try again tomorrow.", ephemeral=True)
            return

        items_master = self.load_json(ITEMS_MASTER_FILE)
        blackmarket_items = self.load_json(BLACKMARKET_FILE)

        # Pools
        items_pool = list(items_master.keys())
        rare_pool = list(blackmarket_items.keys())

        task_desc = random.choice(DAILY_TASKS)
        base_coins = random.randint(40, 80)
        if user.get("boosts", {}).get("coin_doubler"):
            base_coins *= 2
        user["coins"] = user.get("coins", 0) + base_coins
        user["last_task"] = now_str

        loot_boost = user.get("boosts", {}).get("loot_boost", False)
        loot_roll = random.randint(1, 100)
        item_count = 1

        if loot_boost:
            if loot_roll >= 95:
                item_count = 3
            elif loot_roll >= 80:
                item_count = 2

        item_rewards = []

        # 🔧 Always give one guaranteed tool
        guaranteed_tool = random.choice(TOOL_POOL)
        item_rewards.append(guaranteed_tool)
        user.setdefault("stash", []).append(guaranteed_tool)

        # 🎲 Add item rolls (on top of guaranteed tool)
        for _ in range(item_count):
            is_rare = random.randint(1, 100) <= 5
            if is_rare and rare_pool:
                item = random.choice(rare_pool)
            else:
                item = random.choice(items_pool)
            item_rewards.append(item)
            user.setdefault("stash", []).append(item)

        # 🎁 Chance to re-unlock Coin Doubler
        bonus_msgs = []
        if user.get("boosts", {}).get("coin_doubler") and random.randint(1, 100) == 69:
            user["boosts"]["coin_doubler"] = True
            bonus_msgs.append("💥 Lucky draw! You unlocked: **Coin Doubler**!")

        profiles[uid] = user
        self.save_profiles(profiles)

        embed = discord.Embed(title="📋 Daily Task Complete!", color=0x8de68a)
        embed.add_field(name="🧪 Mission", value=task_desc, inline=False)
        embed.add_field(name="💰 Coins Earned", value=f"{base_coins} coins", inline=True)
        embed.add_field(name="📦 Items Gained", value="\n".join([f"🔧 {i}" for i in item_rewards]), inline=False)

        if bonus_msgs:
            embed.add_field(name="🎁 Bonus Rewards", value="\n".join(bonus_msgs), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Task(bot))
