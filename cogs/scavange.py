# cogs/scavenge.py — WARLAB daily gathering logic (3-hour cooldown + boost-aware + counter)

import discord
from discord.ext import commands
from discord import app_commands
import json
import random
from datetime import datetime, timedelta

from utils.fileIO import load_file, save_file
from utils.inventory import weighted_choice
from utils.boosts import is_weekend_boost_active

USER_DATA = "data/user_profiles.json"
RARITY_WEIGHTS = "data/rarity_weights.json"
ITEMS_MASTER = "data/items_master.json"

SCAVENGE_MISSIONS = [
    "Scavenged rare parts from a downed chopper.",
    "Recovered a hidden weapons cache west of Nadbor.",
    "Secured medical supplies from an overrun clinic in Tarnow.",
    "Harvested mutated crops from a contaminated greenhouse in Branzow.",
    "Picked through a derailed supply train south of Gieraltów.",
    "Raided a looted survivor camp deep at Gliniska Airfield.",
    "Salvaged electronics from a rusted comms tower in Sitnik Hills.",
    "Uncovered buried gear beneath a scorched Humvee wreck near Topolin Ridge.",
    "Broke open a sealed weapons crate inside a flooded bunker west of Lukow.",
    "Snuck past gas pockets to grab loot near Kamensk Quarry's blast zone.",
    "Searched beneath a collapsed checkpoint gate near the Zalesie crossing."
]

class Scavenge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="scavenge", description="Scavenge for random materials (cooldown: 3 hours)")
    async def scavenge(self, interaction: discord.Interaction):
        print(f"🟢 /scavenge triggered by {interaction.user.display_name} ({interaction.user.id})")
        await interaction.response.defer(ephemeral=True)

        try:
            user_id = str(interaction.user.id)
            now = datetime.utcnow()

            profiles = await load_file(USER_DATA) or {}
            print(f"📁 Loaded user_profiles.json — {len(profiles)} profiles loaded")

            if user_id not in profiles:
                print(f"❌ User {user_id} not registered")
                await interaction.followup.send("❌ You don’t have a profile yet. Please use `/register` first.", ephemeral=True)
                return

            user = profiles.get(user_id, {})
            user.setdefault("stash", [])
            user.setdefault("coins", 0)
            user.setdefault("last_scavenge", None)
            user.setdefault("boosts", {})
            user.setdefault("scavenges", 0)
            user.setdefault("blueprints", [])

            boosts = user["boosts"]
            pulls = random.randint(2, 5)
            boost_msgs = []
            print(f"🔍 Base pulls: {pulls}")

            if boosts.get("perm_loot_boost"):
                pulls += 1
                boost_msgs.append("💠 Permanent Loot Boost activated!")
                print("✅ perm_loot_boost applied: +1 pull")

            if boosts.get("daily_loot_boost"):
                last_used = user.get("daily_loot_boost_used", "1970-01-01")
                today = now.strftime("%Y-%m-%d")
                if last_used != today:
                    pulls += 1
                    user["daily_loot_boost_used"] = today
                    boost_msgs.append("🔄 Daily Loot Boost activated!")
                    print("✅ daily_loot_boost applied: +1 pull")
                else:
                    print("❌ daily_loot_boost already used today")

            cooldown_min = 180
            if user["last_scavenge"]:
                last_time = datetime.fromisoformat(user["last_scavenge"])
                if now < last_time + timedelta(minutes=cooldown_min):
                    remaining = (last_time + timedelta(minutes=cooldown_min)) - now
                    total_seconds = int(remaining.total_seconds())
                    hrs, rem = divmod(total_seconds, 3600)
                    mins = rem // 60
                    formatted_time = f"**{hrs}h {mins}m**" if hrs else f"**{mins}m**"
                    print(f"⏳ Cooldown active — {formatted_time} remaining")
                    await interaction.followup.send(
                        f"⏳ You must wait {formatted_time} more before scavenging again.",
                        ephemeral=True
                    )
                    return

            item_catalog = await load_file(ITEMS_MASTER)
            rarity_weights = await load_file(RARITY_WEIGHTS)
            owned_blueprints = set(user["blueprints"])
            print(f"📦 Loaded {len(item_catalog)} items")

            loot_pool = []
            for name, data in item_catalog.items():
                if not isinstance(data, dict) or "rarity" not in data:
                    continue
                if data.get("type") == "crafted" and f"{name} Blueprint" in owned_blueprints:
                    continue
                loot_pool.append({"item": name, "rarity": data["rarity"]})

            print(f"🎯 Final loot pool: {len(loot_pool)} entries")

            found = []
            crafted_found = []
            attempts = 0
            max_attempts = 15

            while len(found) < pulls and attempts < max_attempts:
                item = weighted_choice(loot_pool, rarity_weights)
                if not item:
                    print("⚠️ weighted_choice returned None")
                    break
                name = item["item"]
                if name not in found:
                    found.append(name)
                    if item_catalog.get(name, {}).get("type") == "crafted":
                        crafted_found.append(name)
                attempts += 1

            print(f"🎒 Items found: {found}")
            print(f"🧰 Crafted items pulled: {crafted_found}")

            if is_weekend_boost_active():
                bonus = weighted_choice(loot_pool, rarity_weights)
                if bonus:
                    name = bonus["item"]
                    if name not in found:
                        found.append(name)
                        boost_msgs.append("🎁 Weekend Boost activated!")
                        if item_catalog.get(name, {}).get("type") == "crafted":
                            crafted_found.append(name)
                        print(f"🎉 Weekend bonus pulled: {name}")

            coins_found = random.randint(5, 25)
            if boosts.get("coin_doubler"):
                coins_found *= 2
                boost_msgs.append("💸 Coin Doubler applied!")
                print("💵 coin_doubler applied: coins doubled")

            user["stash"].extend(found)
            user["coins"] += coins_found
            user["last_scavenge"] = now.isoformat()
            user["scavenges"] += 1
            profiles[user_id] = user
            await save_file(USER_DATA, profiles)
            print(f"✅ Saved updated profile for {user_id}")

            loot_display = [f"🧰 {x}" if x in crafted_found else x for x in found]
            summary_text = (
                f"📋 {random.choice(SCAVENGE_MISSIONS)}\n\n"
                f"🔎 You scavenged and found: **{', '.join(loot_display)}**\n"
                f"💰 You also found **{coins_found} coins!**\n"
                f"☑️ Scavenges Completed: **{user['scavenges']}**"
            )
            if boost_msgs:
                summary_text += "\n\n" + "\n".join(boost_msgs)

            await interaction.followup.send(summary_text, ephemeral=True)

            if crafted_found:
                for item in crafted_found:
                    await interaction.followup.send(f"🚨 Turn-in ready item pulled! Use `/turnin` to redeem: **{item}**", ephemeral=True)

        except Exception as e:
            print(f"❌ SCAVENGE EXCEPTION: {e}")
            await interaction.followup.send("⚠️ Something went wrong during scavenging. Please contact staff if this persists.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Scavenge(bot))
