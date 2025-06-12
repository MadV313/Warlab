# cogs/raid.py

import discord
from discord.ext import commands
from discord import app_commands
import random
import json
from datetime import datetime, timedelta

COOLDOWN_FILE = "data/raid_cooldowns.json"
USER_DATA_FILE = "data/user_profiles.json"
RAID_LOG_FILE = "data/raid_log.json"

DEFENSE_LIMITS = {
    "barbed_fence": 10,
    "locked_container": 5,
    "reinforced_gate": 5,
    "claymore": 1,
    "guard_dog": 1
}

class Raid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_data(self, path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            return {}

    def save_data(self, path, data):
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def log_raid(self, log_entry):
        logs = self.load_data(RAID_LOG_FILE)
        logs.append(log_entry)
        self.save_data(RAID_LOG_FILE, logs)

    @app_commands.command(name="raid", description="Attempt to raid another player's stash.")
    async def raid(self, interaction: discord.Interaction, target: discord.Member):
        attacker_id = str(interaction.user.id)
        defender_id = str(target.id)
        now = datetime.utcnow()

        if attacker_id == defender_id:
            await interaction.response.send_message("❌ You cannot raid yourself.", ephemeral=True)
            return

        cooldowns = self.load_data(COOLDOWN_FILE)
        users = self.load_data(USER_DATA_FILE)
        attacker = users.get(attacker_id)
        defender = users.get(defender_id)

        if not attacker or not defender:
            await interaction.response.send_message("❌ One of the players has no stash data.", ephemeral=True)
            return

        # --- Retaliation bypass ---
        retaliation_rights = defender.get("retaliation_rights", {}).get(attacker_id)
        is_retaliation = False
        if retaliation_rights:
            is_retaliation = True
            del defender["retaliation_rights"][attacker_id]
        elif defender_id in cooldowns.get(attacker_id, {}):
            last_raid = datetime.fromisoformat(cooldowns[attacker_id][defender_id])
            if now - last_raid < timedelta(hours=24):
                hours_left = 24 - (now - last_raid).seconds // 3600
                await interaction.response.send_message(f"⏳ Wait {hours_left}h before raiding {target.display_name} again.", ephemeral=True)
                return

        # HP check
        defender_hp = defender.get("stash_hp", 100)
        if defender_hp > 40:
            await interaction.response.send_message(f"🛡️ {target.display_name}'s stash is too secure to raid.", ephemeral=True)
            return

        defense = defender.get("defenses", {})
        summary = ["📦 **Defense Report**"]
        blocked = False
        triggered_defenses = []
        stolen_items = []

        for item, max_qty in DEFENSE_LIMITS.items():
            qty = defense.get(item, 0)
            for i in range(qty):
                roll = random.randint(1, 100)
                if item == "guard_dog" and roll <= 50:
                    blocked = True
                    summary.append("🐕 Guard Dog lunged at the raider! Raid blocked.")
                    defense[item] -= 1
                    triggered_defenses.append("Guard Dog")
                    break
                elif item == "claymore" and roll <= 35:
                    blocked = True
                    summary.append("💥 Claymore detonated and stopped the raid!")
                    defense[item] -= 1
                    triggered_defenses.append("Claymore")
                    break
                elif item == "barbed_fence" and roll <= 25:
                    summary.append("🪓 Barbed Fence took damage.")
                    defense[item] -= 1
                    triggered_defenses.append("Barbed Fence")
                elif item == "reinforced_gate" and roll <= 20:
                    summary.append("🚪 Reinforced Gate cracked.")
                    defense[item] -= 1
                    triggered_defenses.append("Reinforced Gate")
                elif item == "locked_container" and roll <= 15:
                    summary.append("🔐 Locked Container absorbed impact.")
                    defense[item] -= 1
                    triggered_defenses.append("Locked Container")

        for item in defense:
            defense[item] = max(defense[item], 0)

        defender["defenses"] = defense

        if blocked:
            result = "❌ **Raid was repelled!**"
            loot_summary = []
        else:
            result = "✅ **Raid successful!**"
            stash = defender.get("stash", [])
            steal_count = min(len(stash), random.randint(1, 3))
            stolen_items = random.sample(stash, steal_count) if stash else []
            for item in stolen_items:
                stash.remove(item)
                attacker.setdefault("stash", []).append(item)
            defender["stash"] = stash
            loot_summary = [f"🎒 Stolen items: `{', '.join(stolen_items)}`" if stolen_items else "⚠️ No loot found."]

            # Retaliation rights granted
            defender.setdefault("retaliation_rights", {})[attacker_id] = now.isoformat()

        # Save updates
        users[attacker_id] = attacker
        users[defender_id] = defender
        self.save_data(USER_DATA_FILE, users)

        if not is_retaliation:
            cooldowns.setdefault(attacker_id, {})[defender_id] = now.isoformat()
            self.save_data(COOLDOWN_FILE, cooldowns)

        # Raid log entry
        self.log_raid({
            "timestamp": now.isoformat(),
            "attacker": attacker_id,
            "defender": defender_id,
            "blocked": blocked,
            "items_stolen": stolen_items,
            "defenses_triggered": triggered_defenses
        })

        # Final message to attacker
        await interaction.response.send_message(
            f"⚔️ **Raid on {target.display_name}**\n{result}\n\n" +
            "\n".join(summary + loot_summary),
            ephemeral=True
        )

        # DM to defender
        try:
            await target.send(
                f"⚠️ **{interaction.user.display_name} raided your stash!**\n{result}\n\n" +
                "\n".join(summary + loot_summary) +
                ("\n\n🔁 You’ve earned 1 retaliation raid. Use `/raid @attacker` within 24h to strike back." if not blocked else "")
            )
        except:
            pass

async def setup(bot):
    await bot.add_cog(Raid(bot))
