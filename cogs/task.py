# cogs/task.py — Daily Warlab mission with crafted item highlights + boost announcements + task counter + persistent storage + debug logs

import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime

from utils.boosts import is_weekend_boost_active
from utils.fileIO import load_file, save_file

USER_DATA_FILE       = "data/user_profiles.json"
ITEMS_MASTER_FILE    = "data/items_master.json"
BLACKMARKET_FILE     = "data/blackmarket_items_master.json"
RECIPE_PATHS         = [
    "data/item_recipes.json",
    "data/armor_blueprints.json",
    "data/explosive_blueprints.json"
]
EMOJI_35 = "<:emoji_35:1372056026840305757>"

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

    async def _load_all_crafted_items(self):
        crafted = set()
        for path in RECIPE_PATHS:
            print(f"📥 Loading crafted items from: {path}")
            data = await load_file(path)
            for entry in data.values():
                output = entry.get("produces")
                if output:
                    crafted.add(output)
        return crafted

    @app_commands.command(name="task", description="Complete your daily Warlab mission for rewards.")
    async def task(self, interaction: discord.Interaction):
        uid       = str(interaction.user.id)
        today_str = datetime.utcnow().strftime("%Y-%m-%d")

        profiles = await load_file(USER_DATA_FILE)
        user = profiles.get(uid)
        if not user:
            await interaction.response.send_message("❌ You don’t have a profile yet. Please use `/register` first.", ephemeral=True)
            return

        if user.get("last_task") == today_str:
            remaining_hours = 24 - datetime.utcnow().hour
            await interaction.response.send_message(
                f"🕒 You’ve already completed your daily task. Try again **tomorrow** (**{remaining_hours}h left**).",
                ephemeral=True
            )
            return

        # ✅ Defer early to avoid timeout
        await interaction.response.defer(ephemeral=True)

        print(f"📅 New task triggered for user {uid} — {interaction.user.display_name}")

        items_master  = await load_file(ITEMS_MASTER_FILE)
        black_market  = await load_file(BLACKMARKET_FILE)
        crafted_set   = await self._load_all_crafted_items()

        blueprint_list = user.get("blueprints", [])
        std_pool  = [item for item in items_master.keys() if item not in blueprint_list]
        rare_pool = [item for item in black_market.keys() if item not in blueprint_list]

        print(f"🎯 STD Pool: {len(std_pool)} items | RARE Pool: {len(rare_pool)} items")

        base_coins = random.randint(40, 80)
        boosts     = user.get("boosts", {})
        active_boosts = []

        if boosts.get("coin_doubler"):
            base_coins *= 2
            active_boosts.append("💰 Coin Doubler")

        user["last_task"] = today_str
        user["coins"] = user.get("coins", 0) + base_coins
        user["tasks_completed"] = user.get("tasks_completed", 0) + 1

        bonus_rolls = 0
        if boosts.get("perm_loot_boost"):
            bonus_rolls += 1
            active_boosts.append("📦 Loot Boost (Permanent)")

        if boosts.get("daily_loot_boost") and user.get("daily_task_loot_used") != today_str:
            bonus_rolls += 1
            active_boosts.append("📦 Loot Boost (Daily)")
            user["daily_task_loot_used"] = today_str

        if is_weekend_boost_active():
            bonus_rolls += 1
            active_boosts.append("<a:bonus:1386436403000512694> Weekend Boost")
            await interaction.followup.send("<a:bonus:1386436403000512694> **Weekend Boost Active!**", ephemeral=True)

        total_rolls = 1 + bonus_rolls
        guaranteed_tool = random.choice(TOOL_POOL)
        item_rewards = [guaranteed_tool]
        crafted_rewards = []

        print(f"🎁 Reward Rolls: {total_rolls} | Guaranteed tool: {guaranteed_tool}")
        user.setdefault("stash", []).append(guaranteed_tool)

        for i in range(total_rolls):
            is_rare = random.randint(1, 100) <= 5
            loot_pool = rare_pool if (is_rare and rare_pool) else std_pool
            if not loot_pool:
                print(f"⚠️ No items in {'rare' if is_rare else 'standard'} pool — skipping roll #{i+1}")
                continue
            loot = random.choice(loot_pool)
            item_rewards.append(loot)
            user["stash"].append(loot)
            if loot in crafted_set:
                crafted_rewards.append(loot)

        item_rewards.sort()

        profiles[uid] = user
        await save_file(USER_DATA_FILE, profiles)
        print(f"✅ Task saved for {interaction.user.display_name} ({uid})")

        mission = random.choice(DAILY_TASKS)
        embed = discord.Embed(title="📋 Daily Task Complete!", color=0x8DE68A)
        embed.add_field(name="🧪 Mission",       value=mission,            inline=False)
        embed.add_field(name="💰 Coins Earned",  value=f"{base_coins}",    inline=True)
        embed.add_field(
            name="📦 Items Gained",
            value="\n".join([f"{'🧰' if itm in crafted_set else '🔧'} {itm}" for itm in item_rewards]),
            inline=False
        )
        embed.add_field(name="✅ Tasks Completed", value=str(user["tasks_completed"]), inline=True)

        if active_boosts:
            embed.add_field(
                name="<a:bonus:1386436403000512694> Active Boosts",
                value="\n".join(active_boosts),
                inline=False
            )

        # ✅ Use followup to respond after deferral
        await interaction.followup.send(embed=embed)

        if crafted_rewards:
            crafted_line = ", ".join([f"**{itm}**" for itm in crafted_rewards])
            await interaction.followup.send(
                f"<a:emoji_71:954381485236961280> Turn-in ready item pulled! Use `/turnin` to redeem: {crafted_line}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Task(bot))
