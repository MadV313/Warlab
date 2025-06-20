# cogs/raid.py — Polished Warlab Raid System (Single Embed Flow + Overlay Merge + 3-Phase Button UI)

import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from datetime import datetime, timedelta
from PIL import Image

from utils.fileIO import load_file, save_file
from utils.boosts import is_weekend_boost_active
from cogs.fortify import render_stash_visual, get_skin_visuals
from stash_image_generator import generate_stash_image

USER_DATA = "data/user_profiles.json"
COOLDOWN_FILE = "data/raid_cooldowns.json"
RAID_LOG_FILE = "data/raid_log.json"
CATALOG_PATH = "data/labskins_catalog.json"
WARLAB_CHANNEL_ID = 1382187883590455296

REINFORCEMENT_ROLLS = {
    "Guard Dog": 50,
    "Claymore Trap": 35,
    "Barbed Fence": 25,
    "Reinforced Gate": 20,
    "Locked Container": 15
}

OVERLAY_GIFS = ["hit.gif", "hit2.gif", "victory.gif"]
MISS_GIF = "miss.gif"

def merge_overlay(base_path, overlay_path, out_path="temp/merged_raid.gif"):
    try:
        base = Image.open(base_path).convert("RGBA")
        overlay = Image.open(overlay_path).convert("RGBA").resize(base.size)
        base.paste(overlay, (0, 0), overlay)
        base.save(out_path, format="GIF")
        return out_path
    except Exception as e:
        print(f"❌ Failed to merge overlay: {e}")
        return overlay_path

class RaidView(discord.ui.View):
    def __init__(self, ctx, attacker, defender, visuals, reinforcements, stash_visual, stash_img_path, is_test_mode, phase=0, target=None):
        super().__init__(timeout=45)
        self.ctx = ctx
        self.attacker = attacker
        self.defender = defender
        self.visuals = visuals
        self.reinforcements = reinforcements
        self.stash_visual = stash_visual
        self.stash_img_path = stash_img_path
        self.is_test_mode = is_test_mode
        self.phase = phase
        self.target = target
        self.triggered = []
        self.success = True
        self.stolen_items = []
        self.stolen_coins = 0
        self.prestige_earned = 0
        self.coin_loss = 0
        self.attacker_id = str(ctx.user.id)
        self.defender_id = str(target.id)
        self.now = datetime.utcnow()

        self.attack_button = discord.ui.Button(label="Attack", style=discord.ButtonStyle.danger)
        self.attack_button.callback = self.attack_phase
        self.add_item(self.attack_button)

    async def attack_phase(self, interaction: discord.Interaction):
        await interaction.response.defer()
        i = self.phase
        hit = True

        for rtype, chance in REINFORCEMENT_ROLLS.items():
            if self.reinforcements.get(rtype, 0) > 0 and random.randint(1, 100) <= chance:
                self.reinforcements[rtype] -= 1
                self.triggered.append(rtype)
                print(f"💥 {rtype} triggered!")
                hit = False
                break

        overlay_name = OVERLAY_GIFS[i] if hit else MISS_GIF
        overlay_path = f"assets/overlays/{overlay_name}"
        merged_path = merge_overlay(self.stash_img_path, overlay_path)

        file = discord.File(merged_path, filename="merged_raid.gif")
        embed = discord.Embed(
            title=f"{self.visuals['emoji']} {self.target.display_name}'s Fortified Lab (Phase {i+1})",
            description=f"```\n{render_stash_visual(self.reinforcements)}\n```",
            color=self.visuals["color"]
        )
        embed.set_image(url="attachment://merged_raid.gif")

        if not hit:
            print("❌ Raid blocked.")
            self.success = False
            self.clear_items()
            self.add_item(discord.ui.Button(label="Close", style=discord.ButtonStyle.secondary, custom_id="close"))
            await interaction.message.edit(embed=embed, attachments=[file], view=self)
            return await self.end_raid(interaction)

        self.phase += 1
        if self.phase == 3:
            self.clear_items()
            self.add_item(discord.ui.Button(label="Close", style=discord.ButtonStyle.secondary, custom_id="close"))
            await interaction.message.edit(embed=embed, attachments=[file], view=self)
            return await self.end_raid(interaction)

        await interaction.message.edit(embed=embed, attachments=[file], view=self)

    async def end_raid(self, interaction: discord.Interaction):
        weekend_bonus = is_weekend_boost_active()
        item_bonus = 1 if weekend_bonus else 0
        coin_multiplier = 1.3 if weekend_bonus else 1.0
        result_summary = []

        if self.success:
            stash = self.defender.get("stash", [])
            max_steal = min(len(stash), random.randint(1, 3 + item_bonus))
            self.stolen_items = random.sample(stash, max_steal) if stash else []
            for item in self.stolen_items:
                stash.remove(item)
                self.attacker.setdefault("stash", []).append(item)
            self.defender["stash"] = stash
            self.stolen_coins = int(random.randint(1, 50) * coin_multiplier)
            self.defender["coins"] = max(0, self.defender.get("coins", 0) - self.stolen_coins)
            self.attacker["coins"] = self.attacker.get("coins", 0) + self.stolen_coins
            self.attacker["raids_successful"] = self.attacker.get("raids_successful", 0) + 1
            self.attacker["prestige_points"] = self.attacker.get("prestige_points", 0) + 50
            self.prestige_earned = 50
            if self.attacker["raids_successful"] >= 25 and "Dark Ops" not in self.attacker.get("labskins", []):
                self.attacker.setdefault("labskins", []).append("Dark Ops")
                result_summary.append("🌑 **Dark Ops** skin unlocked!")
        else:
            self.coin_loss = random.randint(1, 25)
            self.attacker["coins"] = max(0, self.attacker.get("coins", 0) - self.coin_loss)
            result_summary.append(f"💸 You lost **{self.coin_loss} coins** in the failed raid!")

        if self.stolen_items:
            result_summary.append(f"🎒 Items stolen: {', '.join(self.stolen_items)}")
        if self.stolen_coins:
            result_summary.append(f"💰 Coins stolen: {self.stolen_coins}")
        if self.prestige_earned:
            result_summary.append(f"🏅 Prestige gained: {self.prestige_earned}")

        if not self.is_test_mode:
            users = await load_file(USER_DATA)
            cooldowns = await load_file(COOLDOWN_FILE)
            users[self.attacker_id] = self.attacker
            users[self.defender_id] = self.defender
            await save_file(USER_DATA, users)
            cooldowns.setdefault(self.attacker_id, {})[self.defender_id] = self.now.isoformat()
            await save_file(COOLDOWN_FILE, cooldowns)

        await interaction.followup.send(
            f"⚔️ Raid on {self.target.display_name}\n"
            + ("✅ **Raid Successful!**" if self.success else "❌ **Raid Repelled!**")
            + "\n\n" + "\n".join(result_summary),
            ephemeral=True
        )

class Raid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="raid", description="Attempt to raid another player's stash.")
    async def raid(self, interaction: discord.Interaction, target: discord.Member):
        print(f"🛠️ /raid triggered by {interaction.user.display_name} -> Target: {target.display_name}")
        await interaction.response.defer(ephemeral=True)

        attacker_id = str(interaction.user.id)
        defender_id = str(target.id)
        now = datetime.utcnow()
        is_test_mode = target.display_name.lower() == "warlab"

        try:
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
                base_img = catalog[random_skin]["filename"]
                defender = {
                    "labskins": [random_skin],
                    "baseImage": base_img,
                    "reinforcements": {r: random.randint(0, 2) for r in REINFORCEMENT_ROLLS},
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
            embed = discord.Embed(
                title=f"{visuals['emoji']} {target.display_name}'s Fortified Lab",
                description=f"```\n{stash_visual}\n```",
                color=visuals["color"]
            )
            embed.set_image(url="attachment://raid_stash.png")

            view = RaidView(interaction, attacker, defender, visuals, reinforcements, stash_visual, stash_img_path, is_test_mode, target=target)
            await interaction.followup.send(embed=embed, file=file, view=view, ephemeral=True)

        except Exception as e:
            print(f"🔥 RAID EXCEPTION: {e}")
            await interaction.followup.send("⚠️ An error occurred during the raid. Please try again or report to staff.", ephemeral=True)

    async def log_raid(self, entry):
        logs = await load_file(RAID_LOG_FILE) or []
        if not isinstance(logs, list):
            logs = []
        logs.append(entry)
        await save_file(RAID_LOG_FILE, logs)

async def setup(bot):
    await bot.add_cog(Raid(bot))
