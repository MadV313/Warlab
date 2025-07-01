# ---------------------------  Imports / Paths  --------------------------- #
import discord
from discord.ext import commands
from discord import app_commands
import random, os, asyncio
from datetime import datetime, timedelta
from PIL import Image, ImageSequence

from utils.storageClient import load_file, save_file
from utils.boosts import is_weekend_boost_active
from utils.prestigeUtils import apply_prestige_xp, PRESTIGE_TIERS, broadcast_prestige_announcement
from cogs.fortify import render_stash_visual, get_skin_visuals
from stash_image_generator import generate_stash_image

USER_DATA       = "data/user_profiles.json"
COOLDOWN_FILE   = "data/raid_cooldowns.json"
RAID_LOG_FILE   = "data/raid_log.json"
CATALOG_PATH    = "data/labskins_catalog.json"
WARLAB_CHANNEL  = 1382187883590455296
ITEMS_MASTER    = "data/items_master.json"

FORCE_SAVE_TEST_RAID = True  # 🔧 Set to False later to disable test-mode persistence

DEFENCE_TYPES = ["Guard Dog", "Claymore Trap", "Barbed Fence", "Reinforced Gate", "Locked Container"]

WEAPON_PATH     = "data/item_recipes.json"
ARMOR_PATH      = "data/armor_blueprints.json"
EXPLOSIVE_PATH  = "data/explosive_blueprints.json"
RARITY_WEIGHTS  = "data/rarity_weights.json"

OVERLAY_GIFS = ["hit.gif", "hit2.gif", "victory.gif"]
MISS_GIF     = "miss.gif"

RAID_LIMIT = 3  # max raids
RAID_WINDOW_HOURS = 12

# ---------------------- helper: non-blocking countdown ------------------- #
async def countdown_ephemeral(base_msg: str, followup: discord.webhook.WebhookMessage):
    """
    Send a 25-second countdown message that is **ephemeral** and does NOT block
    the raid logic.
    """
    try:
        wait_msg = await followup.send(f"{base_msg} *(25s)*", ephemeral=True)
        for s in range(24, 0, -1):
            await asyncio.sleep(1)
            try:
                await wait_msg.edit(content=f"{base_msg} *({s}s)*")
            except discord.NotFound:
                break
        await wait_msg.delete()
    except Exception:
        pass

# ---------------------------  Helper functions  -------------------------- #
def calculate_block_chance(reinforcements: dict, rtype: str, attacker: dict) -> int:
    count = reinforcements.get(rtype, 0)
    match rtype:
        case "Barbed Fence":      return count * 1
        case "Locked Container":  return count * 2
        case "Reinforced Gate":   return count * 3
        case "Guard Dog":         return 50 if count else 0
        case "Claymore Trap":
            has_pliers = any(item.lower() == "pliers" for item in attacker.get("stash", []))
            return 25 if count and has_pliers else 0
        case _:                   return 0

def merge_overlay(base_path: str, overlay_path: str, out_path: str) -> str:
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        base    = Image.open(base_path).convert("RGBA")
        overlay = Image.open(overlay_path)

        if overlay.is_animated:
            frames = []
            scale_factor = 1.15
            new_size = (int(base.width * scale_factor), int(base.height * scale_factor))
            for frame in ImageSequence.Iterator(overlay):
                frame = frame.convert("RGBA").resize(new_size)
                combined = base.copy()
                pos = ((base.width - frame.width) // 2, (base.height - frame.height) // 2)
                combined.paste(frame, pos, frame)
                frames.append(combined)
            frames[0].save(out_path, save_all=True, append_images=frames[1:], loop=0,
                           duration=overlay.info.get("duration", 100))
        else:
            overlay = overlay.convert("RGBA").resize(base.size)
            base.paste(overlay, (0, 0), overlay)
            base.convert("RGB").save(out_path, "GIF")

        return out_path
    except Exception as e:
        print(f"❌ merge_overlay failed: {e}")
        return base_path

def format_defense_status(reinforcements: dict) -> str:
    emoji_map = {
        "Barbed Fence": "🧱",
        "Locked Container": "🔐",
        "Reinforced Gate": "🚪",
        "Claymore Trap": "💣",
        "Guard Dog": "🐕"
    }
    max_counts = {
        "Barbed Fence": 9,
        "Locked Container": 5,
        "Reinforced Gate": 5,
        "Claymore Trap": 1,
        "Guard Dog": 1
    }

    lines = ["🛡️ **Defense Status**"]
    for key in DEFENCE_TYPES:
        emoji = emoji_map.get(key, "")
        current = reinforcements.get(key, 0)
        max_val = max_counts.get(key, "?")
        lines.append(f"{emoji} {key}: {current}/{max_val}")
    return "\n".join(lines)

async def get_unowned_blueprint(user_profile):
    weapon_pool     = await load_file(WEAPON_PATH)
    armor_pool      = await load_file(ARMOR_PATH)
    explosive_pool  = await load_file(EXPLOSIVE_PATH)
    rarity_weights  = await load_file(RARITY_WEIGHTS)

    all_items = []
    current_blueprints = user_profile.get("blueprints", [])

    for pool in (weapon_pool, armor_pool, explosive_pool):
        for key, entry in pool.items():
            produced = entry.get("produces")
            blueprint_name = f"{produced} Blueprint"
            if produced and blueprint_name not in current_blueprints:
                all_items.append({
                    "item": blueprint_name,
                    "source_key": key,
                    "rarity": entry.get("rarity", "Common")
                })

    if not all_items:
        return None  # No new blueprint available

    from utils.inventory import weighted_choice
    return weighted_choice(all_items, rarity_weights)
    
# ---------------------- Reinforcement Summary Tracker -------------------- #
def summarize_destroyed(start, end, triggered):
    destroyed = []
    for key in start:
        if start[key] > end[key]:
            diff = start[key] - end[key]
            destroyed.append(f"{key} ×{diff}")
    for trap in triggered:
        if trap in start and start[trap] == 1 and end[trap] == 0 and f"{trap} ×1" not in destroyed:
            destroyed.append(f"{trap} ×1")
    return ", ".join(destroyed)

# --------------------- Weekend Bonus Item Helper ------------------------ #
async def get_random_bonus_item():
    try:
        items = await load_file(ITEMS_MASTER)
        if not items:
            return None
        return random.choice(list(items.keys()))
    except Exception as e:
        print(f"⚠️ Failed to load bonus item: {e}")
        return None

# ---------------------------  UI Buttons  ------------------------------- #
class AttackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Attack", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        self.disabled = True
        try:
            await interaction.message.edit(view=self.view)
        except Exception as e:
            print(f"❌ Failed to disable Attack button: {e}")
        await self.view.attack_phase(interaction)

# 🛠️ Updated CloseButton (safe for ephemeral)
class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="❌ Close", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.edit_message(
                content="❌ The Raid UI was closed",
                embed=None,
                attachments=[],
                view=None
            )
        except Exception as e:
            print(f"❌ [CloseButton] Failed to edit message: {e}")
            try:
                await interaction.followup.send("❌ The Raid UI was closed", ephemeral=True)
            except Exception as e2:
                print(f"⛔ Fallback message also failed: {e2}")

# ---------------------------  Main Raid View  ---------------------------- #
class RaidView(discord.ui.View):
    def __init__(self, ctx, attacker, defender, visuals, reinforcements,
                 stash_visual, stash_img_path, is_test_mode, phase=0, target=None):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.attacker = attacker
        self.defender = defender
        self.visuals = visuals
        self.reinforcements = reinforcements
        self.reinforcements_start = reinforcements.copy() if phase == 0 else None
        self.stash_visual = stash_visual
        self.stash_img_path = stash_img_path
        self.is_test_mode = is_test_mode
        self.phase = phase
        self.target = target
        self.results = []
        self.triggered = []
        self.success = True
        self.stolen_items = []
        self.stolen_coins = 0
        self.coin_loss = 0
        self.now = datetime.utcnow()
        self.attacker_id = str(ctx.user.id)
        self.defender_id = str(target.id)
        self.message = None
        self.add_item(AttackButton() if phase < 3 else CloseButton())

#   RaidView METHODS – PASTE OVER THE EXISTING ONES IN FULL          #
# ------------------------------------------------------------------ #
    async def attack_phase(self, interaction: discord.Interaction):
        for item in self.children:
            if isinstance(item, AttackButton):
                item.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except Exception as e:
            print(f"⚠️ button-disable edit failed: {e}")
        await interaction.response.defer(thinking=True, ephemeral=True)
    
        phase_msgs = [
            "<a:ezgif:1385822657852735499> Warlab is recalibrating the targeting system... Stand by!",
            "<a:ezgif:1385822657852735499> Reloading heavy munitions... Stand by!",
            "<a:ezgif:1385822657852735499> Final strike preparing... Stand by!"
        ]
    
        async def countdown(msg: str):
            try:
                wait = await interaction.followup.send(f"{msg} *(25s)*", ephemeral=True)
                for s in range(24, 0, -1):
                    await asyncio.sleep(1)
                    await wait.edit(content=f"{msg} *({s}s)*")
                await wait.delete()
            except Exception as e:
                print(f"⛔ countdown error: {e}")
    
        asyncio.create_task(countdown(phase_msgs[self.phase]))
    
        i = self.phase
        hit = True
        rtype = None
        consumed = False
        dmg = None
    
        for rtype_check in DEFENCE_TYPES:
            ch = calculate_block_chance(self.reinforcements, rtype_check, self.attacker)
            if ch and random.randint(1, 100) <= ch:
                hit = False
                rtype = rtype_check
                self.triggered.append(rtype_check)
                if rtype in ("Guard Dog", "Claymore Trap") or random.random() < 0.5:
                    self.reinforcements[rtype] -= 1
                    consumed = True
                break
    
        if hit:
            viable = [k for k, v in self.reinforcements.items() if v > 0]
            dmg = random.choice(viable) if viable else None
            if dmg and random.random() < 0.8:
                self.reinforcements[dmg] -= 1
                print("🧱 damaged:", dmg)
    
        if any(v < self.reinforcements_start.get(k, 0) for k, v in self.reinforcements.items()):
            self.stash_img_path = generate_stash_image(
                self.defender_id, self.reinforcements,
                base_path="assets/stash_layers",
                baseImagePath=self.defender.get("baseImage") if isinstance(self.defender, dict) else None
            )
    
        self.results.append(hit)
        self.stash_visual = render_stash_visual(self.reinforcements)
    
        overlay = OVERLAY_GIFS[i] if hit else MISS_GIF
        merged_path = f"temp/merged_phase{i+1}_{self.attacker_id}.gif"
        await asyncio.to_thread(merge_overlay, self.stash_img_path, f"assets/overlays/{overlay}", merged_path)
        file = discord.File(merged_path, filename="merged.gif")
    
        phase_titles = ["🔸 Phase 1", "🔸 Phase 2", "🌟 Final Phase"]
        embed = discord.Embed(
            title=f"{self.visuals['emoji']} {self.target.display_name}'s Fortified Stash — {phase_titles[i]}",
            description=f"```{self.stash_visual}```\n\n{format_defense_status(self.reinforcements)}",
        )
        if hit:
            extra = "✅ Attack successful!"
            if dmg:
                extra += f" Destroyed {dmg} ×1."
            embed.description += f"\n\n{extra}"
        else:
            embed.description += f"\n\n💥 {rtype} triggered — attack blocked {'(Consumed ×1)' if consumed else '(Not consumed)'}"
        embed.set_image(url="attachment://merged.gif")
    
        self.phase += 1
        print(f"📊 Phase {i+1} done — Hit={hit}  Trigger={rtype}  Consumed={consumed}")
    
        if self.phase < 3:
            next_view = RaidView(
                self.ctx, self.attacker, self.defender, self.visuals,
                self.reinforcements, self.stash_visual, self.stash_img_path,
                self.is_test_mode, phase=self.phase, target=self.target
            )
            next_view.results = self.results.copy()
            next_view.reinforcements_start = self.reinforcements_start
            next_view.triggered = self.triggered.copy()
            next_view.message = self.message
            try:
                self.message = await self.message.edit(embed=embed, attachments=[file], view=next_view)
            except Exception as e:
                print(f"❌ phase-{self.phase} edit failed: {e}")
            return
    
        print("📊 Phase 3 starting")
        try:
            self.success = self.results.count(True) >= 2
            summary = []
            prestige_gain = 0
            self.stolen_items = []
            self.stolen_coins = 0
        
            if self.success:
                multiplier = 2 if is_weekend_boost_active() else 1
                prestige_gain = 50 * multiplier
                self.stolen_coins = random.randint(5, 25) * multiplier
        
                uid = str(self.attacker_id)
                profiles = await load_file(USER_DATA)
                user = profiles.get(uid, self.attacker)
        
                if is_weekend_boost_active() and all(self.results):
                    user["coins"] += 25
                    bonus_item = await get_random_bonus_item()
                    if bonus_item:
                        user["stash"].append(bonus_item)
                        summary.append(f"<a:bonus_item:1370091021958119445> Bonus item: {bonus_item}")
                    summary.append("<a:bonus:1386436403000512694> Tripple Threat Weekend Boost Active! +25 coins")
        
                defender_stash = self.defender.get("stash", [])
                stealable = [item for item in defender_stash if item not in DEFENCE_TYPES]
        
                if stealable:
                    stolen_count = min(3, len(stealable))
                    self.stolen_items = random.sample(stealable, stolen_count)
                    for item in self.stolen_items:
                        defender_stash.remove(item)
        
                user.setdefault("stash", [])
                print(f"📦 PRE-UPDATE STASH: {user['stash']}")
        
                user["coins"] += self.stolen_coins
                user["stash"].extend(self.stolen_items)
                user["successful_raids"] = user.get("successful_raids", 0) + 1
        
                # ✅ FIXED UNPACKING LINE
                user, ranked_up, rank_msg, _, _ = apply_prestige_xp(user, xp_gain=prestige_gain)
        
                prestige_rank    = user.get("prestige", 0)
                prestige_points  = user.get("prestige_points", 0)
                next_threshold   = PRESTIGE_TIERS.get(prestige_rank + 1)
                summary.append(
                    f"🧬 Prestige: {prestige_rank} — "
                    f"{prestige_points}/{next_threshold if next_threshold else 'MAX'}"
                )
                if ranked_up:
                        try:
                            await broadcast_prestige_announcement(self.ctx.bot, self.ctx.user, user)
                        except Exception as e:
                            print(f"⚠️ Failed to broadcast prestige announcement: {e}")
        
                self.attacker = user
                profiles[uid] = user
                await save_file(USER_DATA, profiles)
    
            final_overlay = "victory.gif" if self.success else "miss.gif"
            final_path = f"temp/final_{self.attacker_id}.gif"
            await asyncio.to_thread(merge_overlay, self.stash_img_path, f"assets/overlays/{final_overlay}", final_path)
            fin_file = discord.File(final_path, filename="final.gif")
    
            fin_title = "🏆 Raid Concluded — Success!" if self.success else "❌ Raid Concluded — Failed"
            fin_embed = discord.Embed(
                title=f"{self.visuals['emoji']} {self.target.display_name}'s Fortified Stash — {fin_title}",
                description = f"```{self.stash_visual}```\n\n{format_defense_status(self.reinforcements)}",
                color=discord.Color.green() if self.success else discord.Color.red()
            )
    
            summary.append(f"🎖️ Prestige gained: +{prestige_gain}")
            if self.stolen_items:
                summary.append(f"🎒 Items stolen: {', '.join(self.stolen_items)}")
            if self.stolen_coins:
                summary.append(f"💰 Coins stolen: {self.stolen_coins}")
            if not self.success:
                current_coins = self.attacker.get("coins", 0)
                if current_coins > -100:
                    penalty = random.randint(1, 25)
                    self.attacker["coins"] = max(current_coins - penalty, -100)
                    print(f"💸 Coin penalty applied: -{penalty}, New balance: {self.attacker['coins']}")
                    summary.append(f"💸 Lost {penalty} coins during the failed raid.")
                else:
                    summary.append("💸 No further penalty — coin balance already at minimum.")
    
            try:
                destroyed = summarize_destroyed(self.reinforcements_start, self.reinforcements, self.triggered)
                if destroyed:
                    summary.append(f"🧱 Defenses destroyed: {destroyed}")
            except Exception as e:
                print(f"⚠️ Failed to summarize destroyed defenses: {e}")
    
            fin_embed.add_field(name="🏁 Raid Summary", value="\n".join(summary), inline=False)
            fin_embed.set_image(url="attachment://final.gif")
    
            final_view = discord.ui.View()
            final_view.add_item(CloseButton())
    
            try:
                await self.message.delete()
            except:
                pass
            self.message = await interaction.followup.send(embed=fin_embed, file=fin_file, view=final_view, ephemeral=True)
    
            try:
                cooldowns = await load_file(COOLDOWN_FILE) or {}
                cooldowns.setdefault(self.attacker_id, {})[self.defender_id] = self.now.isoformat()
                await save_file(COOLDOWN_FILE, cooldowns)
    
            try:
                warlab_channel = self.ctx.guild.get_channel(WARLAB_CHANNEL)
                if warlab_channel:
                    if self.success:
                        await warlab_channel.send(f"⚔️ <@{self.attacker_id}> demolished <@{self.defender_id}>'s stash in a successful raid — stay frosty survivors!")
                    else:
                        await warlab_channel.send(f"🛡️ <@{self.defender_id}> managed to keep <@{self.attacker_id}> away from their goods... maybe they won't be so lucky next time!")
            except Exception as e:
                print(f"⚠️ Failed to broadcast raid result to warlab channel: {e}")
    
            try:
                defender_user = await self.ctx.guild.fetch_member(int(self.defender_id))
                if defender_user and not defender_user.bot and self.success:
                    class RetaliateButton(discord.ui.View):
                        def __init__(self, attacker_id, guild_id):
                            super().__init__(timeout=86400)
                            self.add_item(discord.ui.Button(
                                label="🗡 Retaliate",
                                style=discord.ButtonStyle.danger,
                                url=f"https://discord.com/channels/{guild_id}/{WARLAB_CHANNEL}"
                            ))

                    await defender_user.send(
                        f"⚠️ You were raided by <@{self.attacker_id}>!\nYou may retaliate within 24 hours.",
                        view=RetaliateButton(self.attacker_id, self.ctx.guild.id)
                    )
            except Exception as e:
                print(f"⚠️ Failed to send retaliation DM: {e}")
    
            print(
                f"\n📒 RAID LOG DEBUG\n"
                f"→ Attacker: {self.ctx.user.display_name} ({self.attacker_id})\n"
                f"→ Defender: {self.target.display_name} ({self.defender_id})\n"
                f"→ Result: {'✅ SUCCESS' if self.success else '❌ FAIL'}\n"
                f"→ Triggered: {self.triggered}\n"
                f"→ Reinforcements left: {self.reinforcements}\n"
            )
    
        except Exception as e:
            print(f"🔥 Crash in Phase 3: {e}")

# --------------------------  /raid Command  ------------------------------ #
class Raid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="raid", description="Attempt to raid another player's stash.")
    async def raid(self, interaction: discord.Interaction, target: discord.Member):
        print(f"🛠️ /raid — {interaction.user.display_name} ➜ {target.display_name}")
        await interaction.response.defer(ephemeral=True)

        attacker_id = str(interaction.user.id)
        defender_id = str(target.id)
        now = datetime.utcnow()
        is_test = target.display_name.lower() == "warlab"

        users = await load_file(USER_DATA) or {}
        attacker = users.get(attacker_id)
        if not attacker:
            return await interaction.followup.send("❌ You don’t have a profile yet. Use `/register`.",
                                                   ephemeral=True)

        if attacker_id == defender_id:
            return await interaction.followup.send("❌ You can’t raid yourself.", ephemeral=True)

        # ⏳ Enforce 3-raids-per-12-hours cooldown per attacker
        try:
            raid_window_hours = 12
            raid_limit = 3
            cooldowns = await load_file(COOLDOWN_FILE) or {}
            raid_timestamps = cooldowns.get(attacker_id, [])

            if isinstance(raid_timestamps, dict):
                # Legacy format — skip parsing and avoid crash
                print(f"⚠️ Skipping legacy cooldown format for {attacker_id}")
                raid_timestamps = []

            recent_raids = []
            for ts in raid_timestamps:
                try:
                    parsed = datetime.fromisoformat(ts)
                    if now - parsed <= timedelta(hours=raid_window_hours):
                        recent_raids.append(parsed)
                except ValueError:
                    print(f"⚠️ Skipping malformed timestamp in cooldowns: {ts}")

            if len(recent_raids) >= raid_limit:
                return await interaction.followup.send(
                    f"🚫 You’ve already raided 3 times in the past {raid_window_hours} hours.\nTry again later.",
                    ephemeral=True
                )

            # ✅ Log this new raid timestamp
            recent_raids.append(now)
            cooldowns[attacker_id] = [ts.isoformat() for ts in recent_raids]
            await save_file(COOLDOWN_FILE, cooldowns)

        except Exception as e:
            print(f"⚠️ Failed raid cooldown check: {e}")

        # Setup test or real defender
        if is_test:
            catalog = await load_file(CATALOG_PATH) or {}
            skin = random.choice(list(catalog))
            defender = {
                "labskins": [skin],
                "baseImage": catalog[skin]["filename"],
                "reinforcements": {
                    "Guard Dog": 1,
                    "Claymore Trap": 1,
                    "Barbed Fence": 2,
                    "Reinforced Gate": 1,
                    "Locked Container": 1
                },
                "stash": ["Saw", "Red Dot", "NBC Suit"],
                "coins": 50
            }
        else:
            defender = users.get(defender_id)
            if not defender:
                return await interaction.followup.send(
                    "❌ That player doesn’t have a profile yet.", ephemeral=True)

        reinforcements = defender.get("reinforcements", {})
        catalog = await load_file(CATALOG_PATH) or {}
        visuals = get_skin_visuals(defender, catalog)
        stash_visual = render_stash_visual(reinforcements)

        stash_img_path = generate_stash_image(
            defender_id, reinforcements,
            base_path="assets/stash_layers",
            baseImagePath=defender.get("baseImage")
        )

        file = discord.File(stash_img_path, "raid_stash.png")
        embed = discord.Embed(
            title=f"{visuals['emoji']} {target.display_name}'s Fortified Stash",
            description=f"""```\n{stash_visual}\n```""",
            color=visuals["color"]
        ).set_image(url="attachment://raid_stash.png")

        view = RaidView(interaction, attacker, defender, visuals, reinforcements,
                        stash_visual, stash_img_path, is_test, target=target)

        initial_msg = await interaction.followup.send(embed=embed, file=file, view=view, ephemeral=True)
        view.message = initial_msg

# ---------------------------  Cog Setup  --------------------------------- #
async def setup(bot): await bot.add_cog(Raid(bot))
