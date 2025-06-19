# cogs/raid.py — Updated Warlab Raid System with Overlays, Risk, Prestige, Unlocks

import discord
from discord.ext import commands
from discord import app_commands
import random
import json
from datetime import datetime, timedelta
import asyncio

from utils.boosts import is_weekend_boost_active

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

    def load(self, path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            return {} if path.endswith(".json") else []

    def save(self, path, data):
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @app_commands.command(name="raid", description="Attempt to raid another player's stash.")
    async def raid(self, interaction: discord.Interaction, target: discord.Member):
        attacker_id = str(interaction.user.id)
        defender_id = str(target.id)
        now = datetime.utcnow()

        if attacker_id == defender_id:
            await interaction.response.send_message("❌ You cannot raid yourself.", ephemeral=True)
            return

        cooldowns = self.load(COOLDOWN_FILE)
        users = self.load(USER_DATA)
        attacker = users.get(attacker_id)
        defender = users.get(defender_id)

        if not attacker:
            await interaction.response.send_message("❌ You don’t have a profile yet. Use `/register`.", ephemeral=True)
            return
        if not defender:
            await interaction.response.send_message("❌ That player doesn’t have a profile yet.", ephemeral=True)
            return

        last_attacks = cooldowns.get(attacker_id, {})
        if defender_id in last_attacks:
            last_time = datetime.fromisoformat(last_attacks[defender_id])
            if now - last_time < timedelta(hours=24):
                wait = timedelta(hours=24) - (now - last_time)
                await interaction.response.send_message(f"⏳ Wait {wait.seconds//3600}h before raiding this player again.", ephemeral=True)
                return
        elif attacker_id in cooldowns and now - datetime.fromisoformat(list(last_attacks.values())[-1]) < timedelta(hours=3):
            await interaction.response.send_message(f"⏳ Wait before raiding again (3h cooldown).", ephemeral=True)
            return

        reinforcements = defender.get("reinforcements", {})
        visual_embed = discord.Embed(
            title=f"🏚️ {target.display_name}'s Fortified Lab",
            description=f"```{self.render_stash(reinforcements)}```",
            color=0x95a5a6
        )
        await interaction.response.send_message(embed=visual_embed, ephemeral=True)

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
            # ⏺️ Add visual animation placeholders
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

            stolen_coins = random.randint(1, 50)
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

        users[attacker_id] = attacker
        users[defender_id] = defender
        self.save(USER_DATA, users)
        cooldowns.setdefault(attacker_id, {})[defender_id] = now.isoformat()
        self.save(COOLDOWN_FILE, cooldowns)
        self.log_raid({
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
            await target.send(f"⚠️ {interaction.user.display_name} raided your stash!\n{outcome}\n\n" + "\n".join(result_summary))
        except:
            pass

    def render_stash(self, reinforcements):
        bf = reinforcements.get("Barbed Fence", 0)
        lc = reinforcements.get("Locked Container", 0)
        rg = reinforcements.get("Reinforced Gate", 0)
        gd = reinforcements.get("Guard Dog", 0)
        cm = reinforcements.get("Claymore Trap", 0)

        row1 = " ".join(["🧱" if i < bf else "🔲" for i in range(5)])
        row2 = " ".join(["🔐" if i < lc else "🔲" for i in range(5)])
        row3 = " ".join(["🚪" if i < rg else "🔲" for i in range(5)])
        row4 = f"🐶 x{gd}" if gd else ""
        row5 = f"💣 x{cm}" if cm else ""

        return f"{row1}\n{row2}\n{row3}\n{row4} {row5}"

    def log_raid(self, entry):
        logs = self.load(RAID_LOG_FILE)
        if not isinstance(logs, list):
            logs = []
        logs.append(entry)
        self.save(RAID_LOG_FILE, logs)

async def setup(bot):
    await bot.add_cog(Raid(bot))
