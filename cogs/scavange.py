# cogs/scavenge.py — WARLAB daily gathering logic (dynamic loot + coins + debug)

import discord
from discord.ext import commands
from discord import app_commands
import json
import random
from datetime import datetime, timedelta

from utils.fileIO import load_file, save_file
from utils.inventory import weighted_choice

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
            user = profiles.get(user_id, {})
            user.setdefault("stash", [])
            user.setdefault("coins", 0)
            user.setdefault("last_scavenge", None)

            # Cooldown: 3 hours = 180 minutes
            cooldown_min = 180
            if user["last_scavenge"]:
                last_time = datetime.fromisoformat(user["last_scavenge"])
                if now < last_time + timedelta(minutes=cooldown_min):
                    remaining = (last_time + timedelta(minutes=cooldown_min)) - now
                    mins = int(remaining.total_seconds() // 60)
                    print(f"⏳ Cooldown active: {mins} mins remaining")
                    await interaction.followup.send(f"⏳ You must wait {mins} more minutes before scavenging again.", ephemeral=True)
                    return

            # Load master item pool and rarity weights
            item_catalog = await load_file(ITEMS_MASTER)
            rarity_weights = await load_file(RARITY_WEIGHTS)
            print(f"📦 Item catalog size: {len(item_catalog)}")
            print(f"📊 Rarity weights: {rarity_weights}")

            # Prepare weighted pool
            loot_pool = [{"item": k, "rarity": v["rarity"]} for k, v in item_catalog.items() if "rarity" in v]

            found = []
            pulls = random.randint(2, 5)
            for i in range(pulls):
                item = weighted_choice(loot_pool, rarity_weights)
                if item:
                    item_name = item["item"] if isinstance(item, dict) else item
                    print(f"🎯 Pull {i+1}: {item_name}")
                    found.append(item_name)

            # Roll coin bonus
            coins_found = random.randint(5, 25)
            user["coins"] += coins_found

            # Weekend bonus
            if now.weekday() in [5, 6]:
                print("🎉 Weekend bonus triggered")
                bonus = weighted_choice(loot_pool, rarity_weights)
                if bonus:
                    bonus_name = bonus["item"] if isinstance(bonus, dict) else bonus
                    print(f"🎁 Weekend Bonus: {bonus_name}")
                    found.append(bonus_name)

            # Update profile
            user["stash"].extend(found)
            user["last_scavenge"] = now.isoformat()
            profiles[user_id] = user
            await save_file(USER_DATA, profiles)

            mission_text = random.choice(SCAVENGE_MISSIONS)

            if found:
                print(f"📦 Items found: {found} + 💰 {coins_found} coins")
                await interaction.followup.send(
                    f"📋 {mission_text}\n\n"
                    f"🔎 You scavenged and found: **{', '.join(found)}**\n"
                    f"💰 You also found **{coins_found} coins!**",
                    ephemeral=True
                )
            else:
                print("📭 No items found, but coins granted")
                await interaction.followup.send(
                    f"📋 {mission_text}\n\n"
                    f"🔎 You didn’t find any items, but gained 💰 **{coins_found} coins!**",
                    ephemeral=True
                )

        except Exception as e:
            print(f"❌ SCAVENGE EXCEPTION: {e}")
            await interaction.followup.send("⚠️ Something went wrong during scavenging.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Scave_
