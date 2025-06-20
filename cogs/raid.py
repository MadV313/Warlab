# cogs/raid.py — Polished Warlab Raid System (Visual Stash Rendering + Test Mode)

import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from datetime import datetime, timedelta

from utils.fileIO import load_file, save_file
from utils.boosts import is_weekend_boost_active
from cogs.fortify import render_stash_visual, get_skin_visuals
from stash_image_generator import generate_stash_image

USER_DATA = "data/user_profiles.json"
COOLDOWN_FILE = "data/raid_cooldowns.json"
RAID_LOG_FILE = "data/raid_log.json"
CATALOG_PATH = "data/labskin_catalog.json"
WARLAB_CHANNEL_ID = 1382187883590455296

REINFORCEMENT_ROLLS = {
    "Guard Dog": 50,
    "Claymore Trap": 35,
    "Barbed Fence": 25,
    "Reinforced Gate": 20,
    "Locked Container": 15
}

class Raid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="raid", description="Attempt to raid another player's stash.")
    async def raid(self, interaction: discord.Interaction, target: discord.Member):
        await interaction.response.defer(ephemeral=True)
        attacker_id = str(interaction.user.id)
        defender_id = str(target.id)
        now = datetime.utcnow()
        is_test_mode = target.display_name.lower() == "warlab"

        if attacker_id == defender_id:
            await interaction.followup.send("❌ You cannot raid yourself.", ephemeral=True)
            return

        cooldowns = await load_file(COOLDOWN_FILE) or {}
        users = await load_file(USER_DATA) or {}
        attacker = users.get(attacker_id)

        if not attacker:
            await interaction.followup.send("❌ You don’t have a profile yet. Use `/register`.", ephemeral=True)
            return

        if is_test_mode:
            catalog = await load_file(CATALOG_PATH) or {}
            random_skin = random.choice(list(catalog.keys()))
            base_img = catalog[random_skin]["baseImage"]
            defender = {
                "labskins": [random_skin],
                "baseImage": base_img,
                "reinforcements": {
                    "Guard Dog": random.randint(0, 1),
                    "Claymore Trap": random.randint(0, 2),
                    "Barbed Fence": random.randint(0, 4),
                    "Reinforced Gate": random.randint(0, 3),
                    "Locked Container": random.randint(0, 2)
                },
                "stash": [f"TestItem{i}" for i in range(random.randint(1, 5))],
                "coins": random.randint(10, 75)
            }
        else:
            defender = users.get(defender_id)
            if not defender:
                await interaction.followup.send("❌ That player doesn’t have a profile yet.", ephemeral=True)
                return

            last_attacks = cooldowns.get(attacker_id, {})
            if defender_id in last_attacks:
                last_time = datetime.fromisoformat(last_attacks[defender_id])
                if now - last_time < timedelta(hours=24):
                    wait = timedelta(hours=24) - (now - last_time)
                    await interaction.followup.send(f"⏳ Wait {wait.seconds//3600}h before raiding this player again.", ephemeral=True)
                    return
            elif attacker_id in cooldowns and now - datetime.fromisoformat(list(last_attacks.values())[-1]) < timedelta(hours=3):
                await interaction.followup.send("⏳ Wait before raiding again (3h cooldown).", ephemeral=True)
                return

        reinforcements = defender.get("reinforcements", {})
        catalog = await load_file(CATALOG_PATH) or {}
        visuals = get_skin_visuals(defender, catalog)
        stash_visual = render_stash_visual(reinforcements)

        stash_img_path = generate_stash_image(
            defender_id,
            reinforcements,
            base_path="assets/stash_layers",
            baseImagePath=defender.get("baseImage")
        )
        file = discord.File(stash_img_path, filename="raid_stash.png")

        visual_embed = discord.Embed(
            title=f"{visuals['emoji']} {target.display_name}'s Fortified Lab",
            description=f"```\n{stash_visual}\n```",
            color=visuals["color"]
        )
        visual_embed.set_image(url="attachment://raid_stash.png")
        await interaction.followup.send(embed=visual_embed, file=file, ephemeral=True)
        await asyncio.sleep(1)

        result_summary = []
        triggered = []
        success = True

        for i in range(3):
            hit = True
            for rtype, chance in REINFORCEMENT_ROLLS.items():
                if reinforcements.get(rtype, 0) > 0 and random.randint(1, 100) <= chance:
                    reinforcements[rtype] -= 1
                    triggered.append(rtype)
                    hit = False
                    break
            await interaction.followup.send(f"🎞️ Roll {i+1}: {'✅ HIT' if hit else '❌ BLOCKED'}", ephemeral=True)
            await asyncio.sleep(1)
            if not hit:
                success = False
                break

        weekend_bonus = is_weekend_boost_active()
        item_bonus = 1 if weekend_bonus else 0
        coin_multiplier = 1.3 if weekend_bonus else 1.0

        stolen_items = []
        stolen_coins = 0
        prestige_earned = 0
        coin_loss = 0

        if success:
            stash = defender.get("stash", [])
            max_steal = min(len(stash), random.randint(1, 3 + item_bonus))
            stolen_items = random.sample(stash, max_steal) if stash else []

            for item in stolen_items:
                stash.remove(item)
                attacker.setdefault("stash", []).append(item)
            defender["stash"] = stash

            stolen_coins = int(random.randint(1, 50) * coin_multiplier)
            defender["coins"] = max(0, defender.get("coins", 0) - stolen_coins)
            attacker["coins"] = attacker.get("coins", 0) + stolen_coins

            attacker["raids_successful"] = attacker.get("raids_successful", 0) + 1
            attacker["prestige_points"] = attacker.get("prestige_points", 0) + 50
            prestige_earned = 50

            if attacker["raids_successful"] >= 25 and "Dark Ops" not in attacker.get("labskins", []):
                attacker.setdefault("labskins", []).append("Dark Ops")
                result_summary.append("🌑 **Dark Ops** skin unlocked!")

        else:
            coin_loss = random.randint(1, 25)
            attacker["coins"] = max(0, attacker.get("coins", 0) - coin_loss)
            result_summary.append(f"💸 You lost **{coin_loss} coins** in the failed raid!")

        if stolen_items:
            result_summary.append(f"🎒 Items stolen: {', '.join(stolen_items)}")
        if stolen_coins:
            result_summary.append(f"💰 Coins stolen: {stolen_coins}")
        if prestige_earned:
            result_summary.append(f"🏅 Prestige gained: {prestige_earned}")

        if not is_test_mode:
            users[attacker_id] = attacker
            users[defender_id] = defender
            await save_file(USER_DATA, users)
            cooldowns.setdefault(attacker_id, {})[defender_id] = now.isoformat()
            await save_file(COOLDOWN_FILE, cooldowns)
            await self.log_raid({
                "timestamp": now.isoformat(),
                "attacker": attacker_id,
                "defender": defender_id,
                "blocked": not success,
                "items": stolen_items,
                "coins": stolen_coins,
                "lost_coins": coin_loss,
                "prestige": prestige_earned,
                "defenses_triggered": triggered
            })

        outcome = "✅ **Raid Successful!**" if success else "❌ **Raid Repelled!**"
        await interaction.followup.send(f"⚔️ Raid on {target.display_name}\n{outcome}\n\n" + "\n".join(result_summary), ephemeral=True)

        try:
            if not is_test_mode:
                await target.send(f"⚠️ {interaction.user.display_name} raided your stash!\n{outcome}\n\n" + "\n".join(result_summary))
        except:
            pass

    async def log_raid(self, entry):
        logs = await load_file(RAID_LOG_FILE) or []
        if not isinstance(logs, list):
            logs = []
        logs.append(entry)
        await save_file(RAID_LOG_FILE, logs)

async def setup(bot):
    await bot.add_cog(Raid(bot))
