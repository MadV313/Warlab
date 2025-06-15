# cogs/raid.py — Updated Warlab Raid System with Visuals, Retaliation, and Broadcasts

import discord
from discord.ext import commands
from discord import app_commands
import random
import json
from datetime import datetime, timedelta
from urllib.parse import quote

USER_DATA = "data/user_profiles.json"
COOLDOWN_FILE = "data/raid_cooldowns.json"
RAID_LOG_FILE = "data/raid_log.json"
CATALOG_PATH = "data/labskin_catalog.json"
WARLAB_CHANNEL_ID = 1382187883590455296
FORTIFY_UI_URL = "https://madv313.github.io/Stash-Fortify-UI/?data="

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

        if not attacker or not defender:
            await interaction.response.send_message("❌ One of the players has no profile.", ephemeral=True)
            return

        last_attacks = cooldowns.get(attacker_id, {})
        cooldown_time = timedelta(hours=12 if defender_id in last_attacks else 3)
        if defender_id in last_attacks:
            last_time = datetime.fromisoformat(last_attacks[defender_id])
            if now - last_time < cooldown_time:
                wait = cooldown_time - (now - last_time)
                await interaction.response.send_message(f"⏳ You must wait {wait.seconds // 3600}h to raid this player again.", ephemeral=True)
                return

        reinforcements = defender.get("reinforcements", {})
        stash_hp = defender.get("stash_hp", 0)
        visual_embed = discord.Embed(
            title=f"🔐 {target.display_name}'s Fortified Stash",
            description=f"""
```
{self.render_stash(reinforcements)}
```""",
            color=0x95a5a6
        )
        await interaction.response.send_message(embed=visual_embed, ephemeral=True)

        triggered = []
        blocked = False
        roll_attempts = 3

        for attempt in range(roll_attempts):
            for dtype, chance in REINFORCEMENT_ROLLS.items():
                qty = reinforcements.get(dtype, 0)
                if qty > 0 and random.randint(1, 100) <= chance:
                    reinforcements[dtype] -= 1
                    blocked = True
                    triggered.append(dtype)
                    break
            if blocked:
                break
            # Refresh updated visual per attempt
            visual_embed.description = f"""
```
{self.render_stash(reinforcements)}
```"""
            await interaction.edit_original_response(embed=visual_embed)
            await discord.utils.sleep_until(datetime.utcnow() + timedelta(seconds=1))

        stolen = []
        result_summary = []

        if blocked:
            result = f"❌ Raid repelled by {', '.join(triggered)}!"
        else:
            result = "✅ Raid successful!"
            inv = defender.get("inventory", [])
            steal_count = min(len(inv), random.randint(1, 3))
            stolen = random.sample(inv, steal_count) if inv else []
            for item in stolen:
                inv.remove(item)
                attacker.setdefault("inventory", []).append(item)
            defender["inventory"] = inv
            attacker["successful_raids"] = attacker.get("successful_raids", 0) + 1
            result_summary.append(f"🎒 Items stolen: `{', '.join(stolen)}`" if stolen else "⚠️ No items found.")
            defender.setdefault("retaliation_rights", {})[attacker_id] = now.isoformat()

        users[attacker_id] = attacker
        users[defender_id] = defender
        self.save(USER_DATA, users)
        cooldowns.setdefault(attacker_id, {})[defender_id] = now.isoformat()
        self.save(COOLDOWN_FILE, cooldowns)

        self.log_raid({
            "timestamp": now.isoformat(),
            "attacker": attacker_id,
            "defender": defender_id,
            "blocked": blocked,
            "items": stolen,
            "defenses_triggered": triggered
        })

        channel = self.bot.get_channel(WARLAB_CHANNEL_ID)
        if channel:
            await channel.send(f"📣 **{interaction.user.display_name} raided {target.display_name}!**\n{result}")

        await interaction.followup.send(
            f"⚔️ **Raid on {target.display_name}**\n{result}\n\n" + "\n".join(result_summary), ephemeral=True
        )

        try:
            await target.send(
                f"⚠️ {interaction.user.display_name} raided your stash!\n{result}\n\n" +
                "\n".join(result_summary) +
                ("\n\n🔁 You may retaliate using `/raid` within 24h." if not blocked else "")
            )
        except:
            pass

    def render_stash(self, reinforcements):
        bf = reinforcements.get("Barbed Fence", 0)
        lc = reinforcements.get("Locked Container", 0)
        rg = reinforcements.get("Reinforced Gate", 0)
        gd = reinforcements.get("Guard Dog", 0)
        cm = reinforcements.get("Claymore Trap", 0)

        lc_slots = ["🔐" if i < lc else "🔲" for i in range(5)]
        rg_row = " ".join(["🚪" if i < rg else "🔲" for i in range(5)])
        bf_emojis = ["🧱" if i < bf else "🔲" for i in range(9)]
        dog = "🐶" if gd else "🔲"
        clay = "💣" if cm else "🔲"

        row1 = f"{bf_emojis[0]} {bf_emojis[1]} {bf_emojis[2]} {bf_emojis[3]} {bf_emojis[4]}"
        row2 = f"{bf_emojis[5]} {lc_slots[0]} {lc_slots[1]} {lc_slots[2]} {bf_emojis[6]}"
        row3 = f"{bf_emojis[7]} {lc_slots[3]} 📦 {lc_slots[4]} {bf_emojis[8]}"
        row4 = rg_row
        row5 = f"  {dog}       {clay}"

        return f"{row1}\n{row2}\n{row3}\n{row4}\n{row5}"

    def log_raid(self, entry):
        logs = self.load(RAID_LOG_FILE)
        if not isinstance(logs, list): logs = []
        logs.append(entry)
        self.save(RAID_LOG_FILE, logs)

async def setup(bot):
    await bot.add_cog(Raid(bot))
