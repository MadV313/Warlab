# cogs/scavenge.py — WARLAB daily gathering logic (dynamic loot + coins + debug)

import discord
from discord.ext import commands
from discord import app_commands
import json
import random
from datetime import datetime, timedelta

from utils.fileIO import load_file, save_file
from utils.inventory import weighted_choice
from utils.boosts import is_weekend_boost_active  # ✅ Boost helper

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
            print(f"📁 Loaded user_profiles.json: {list(profiles.keys())}")

            if user_id not in profiles:
                await interaction.followup.send("❌ You don’t have a profile yet. Please use `/register` first.", ephemeral=True)
                return

            user = profiles.get(user_id, {})
            user.setdefault("stash", [])
            user.setdefault("coins", 0)
            user.setdefault("last_scavenge", None)
            user.setdefault("boosts", {})
            user.setdefault("scavenges", 0)

            boosts = user.get("boosts", {})
            pulls = random.randint(2, 5)
            if boosts.get("perm_loot_boost"):
                pulls += 1
            if boosts.get("daily_loot_boost"):
                last_date = user.get("daily_loot_boost_used", "1970-01-01")
                if last_date != now.strftime("%Y-%m-%d"):
                    pulls += 1
                    user["daily_loot_boost_used"] = now.strftime("%Y-%m-%d")

            # Cooldown
            cooldown_min = 180
            if user["last_scavenge"]:
                last_time = datetime.fromisoformat(user["last_scavenge"])
                if now < last_time + timedelta(minutes=cooldown_min):
                    remaining = (last_time + timedelta(minutes=cooldown_min)) - now
                    mins = int(remaining.total_seconds() // 60)
                    await interaction.followup.send(f"⏳ You must wait {mins} more minutes before scavenging again.", ephemeral=True)
                    return

            # Load item pool and weights
            item_catalog = await load_file(ITEMS_MASTER)
            rarity_weights = await load_file(RARITY_WEIGHTS)
            loot_pool = [{"item": k, "rarity": v["rarity"]} for k, v in item_catalog.items() if isinstance(v, dict) and "rarity" in v]

            found = []
            crafted_found = []  # 🧰 For turn-in-ready detection
            for i in range(pulls):
                item = weighted_choice(loot_pool, rarity_weights)
                if item:
                    name = item["item"]
                    found.append(name)
                    item_type = item_catalog.get(name, {}).get("type", "")
                    if item_type == "crafted":
                        crafted_found.append(name)

            # Weekend bonus
            if is_weekend_boost_active():
                bonus = weighted_choice(loot_pool, rarity_weights)
                if bonus:
                    name = bonus["item"]
                    found.append(name)
                    if item_catalog.get(name, {}).get("type", "") == "crafted":
                        crafted_found.append(name)

            coins_found = random.randint(5, 25)
            if boosts.get("coin_doubler"):
                coins_found *= 2

            user["stash"].extend(found)
            user["coins"] += coins_found
            user["last_scavenge"] = now.isoformat()
            user["scavenges"] += 1  # ✅ Count tracked
            profiles[user_id] = user
            await save_file(USER_DATA, profiles)

            # 🧾 Format embed with 🧰 marker
            mission_text = random.choice(SCAVENGE_MISSIONS)
            display_loot = []
            for item in found:
                if item in crafted_found:
                    display_loot.append(f"🧰 {item}")
                else:
                    display_loot.append(item)

            await interaction.followup.send(
                f"📋 {mission_text}\n\n"
                f"🔎 You scavenged and found: **{', '.join(display_loot)}**\n"
                f"💰 You also found **{coins_found} coins!**",
                ephemeral=True
            )

            if crafted_found:
                for turnin_item in crafted_found:
                    await interaction.followup.send(
                        f"🚨 Turn-in ready item pulled! Use `/turnin` to redeem: **{turnin_item}**",
                        ephemeral=True
                    )

        except Exception as e:
            print(f"❌ SCAVENGE EXCEPTION: {e}")
            await interaction.followup.send("⚠️ Something went wrong during scavenging. Please contact staff if this persists.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Scavenge(bot))
