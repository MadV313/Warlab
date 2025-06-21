# ---------------------------  Imports / Paths  --------------------------- #
import discord
from discord.ext import commands
from discord import app_commands
import random, os, asyncio
from datetime import datetime, timedelta
from PIL import Image, ImageSequence

from utils.fileIO import load_file, save_file
from utils.boosts import is_weekend_boost_active
from cogs.fortify import render_stash_visual, get_skin_visuals
from stash_image_generator import generate_stash_image

USER_DATA       = "data/user_profiles.json"
COOLDOWN_FILE   = "data/raid_cooldowns.json"
RAID_LOG_FILE   = "data/raid_log.json"
CATALOG_PATH    = "data/labskins_catalog.json"
WARLAB_CHANNEL  = 1382187883590455296

DEFENCE_TYPES = ["Guard Dog", "Claymore Trap", "Barbed Fence", "Reinforced Gate", "Locked Container"]

OVERLAY_GIFS = ["hit.gif", "hit2.gif", "victory.gif"]
MISS_GIF     = "miss.gif"

# ---------------------- helper: non-blocking countdown ------------------- #
async def countdown_ephemeral(base_msg: str, followup: discord.webhook.WebhookMessage):
    """
    Send a 20-second countdown message that is **ephemeral** and does NOT block
    the raid logic.
    """
    try:
        wait_msg = await followup.send(f"{base_msg} *(20s)*", ephemeral=True)
        for s in range(19, 0, -1):
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

# ---------------------------  UI Buttons  ------------------------------- #
class AttackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Attack", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        view: "RaidView" = self.view
        await view.attack_phase(interaction)

class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.message.delete()

# ---------------------------  Main Raid View  ---------------------------- #
class RaidView(discord.ui.View):
    def __init__(self, ctx, attacker, defender, visuals, reinforcements,
                 stash_visual, stash_img_path, is_test_mode, phase=0, target=None):
        super().__init__(timeout=None)
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
        self.results = []
        self.triggered = []
        self.success = True
        self.stolen_items = []
        self.stolen_coins = 0
        self.prestige_earned = 0
        self.coin_loss = 0
        self.now = datetime.utcnow()
        self.attacker_id = str(ctx.user.id)
        self.defender_id = str(target.id)
        self.message = None  # Used to track the original embed message

        self.add_item(AttackButton() if phase < 3 else CloseButton())

    # --------------------------------------------------------------------- #
    async def attack_phase(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
    
        phase_msgs = [
            "<a:ezgif:1385822657852735499> Warlab is recalibrating the targeting system... Stand by!",
            "<a:ezgif:1385822657852735499> Reloading heavy munitions... Stand by!",
            "<a:ezgif:1385822657852735499> Final strike preparing... Stand by!"
        ]
    
        if self.phase < 3:
            base_msg = phase_msgs[self.phase]
    
            async def countdown_ephemeral(base_msg, followup):
                try:
                    wait_msg = await followup.send(content=f"{base_msg} *(10s)*", ephemeral=True)
                    for seconds in range(9, 0, -1):
                        await asyncio.sleep(1)
                        try:
                            await wait_msg.edit(content=f"{base_msg} *({seconds}s)*")
                        except discord.NotFound:
                            break
                    try:
                        await wait_msg.delete()
                    except discord.NotFound:
                        pass
                except Exception as e:
                    print(f"⛔ Countdown error: {e}")
    
            asyncio.create_task(countdown_ephemeral(base_msg, interaction.followup))
    
            # === ROLL LOGIC ===
            i = self.phase
            hit = True
            rtype = None
            consumed = False
    
            for rtype_check in DEFENCE_TYPES:
                chance = calculate_block_chance(self.reinforcements, rtype_check, self.attacker)
                if chance and random.randint(1, 100) <= chance:
                    rtype = rtype_check
                    hit = False
                    self.triggered.append(rtype_check)
                    if rtype in ["Guard Dog", "Claymore Trap"] or random.random() < 0.5:
                        self.reinforcements[rtype] -= 1
                        consumed = True
                    break
    
            if hit:
                valid_dmg_targets = [r for r in DEFENCE_TYPES if self.reinforcements.get(r, 0) > 0]
                maybe_damage = random.choice(valid_dmg_targets) if valid_dmg_targets else None
                if maybe_damage and random.random() < 0.8:
                    self.reinforcements[maybe_damage] -= 1
                    print(f"🧱 Reinforcement damaged due to success: {maybe_damage}")
    
            if any(v == 0 for v in self.reinforcements.values()):
                self.stash_img_path = generate_stash_image(
                    self.defender_id, self.reinforcements,
                    base_path="assets/stash_layers",
                    baseImagePath=self.defender.get("baseImage")
                )
    
            self.results.append(hit)
            self.stash_visual = render_stash_visual(self.reinforcements)
    
            overlay_path = f"assets/overlays/{OVERLAY_GIFS[i] if hit else MISS_GIF}"
            merged_path = f"temp/merged_phase{i+1}_{self.attacker_id}.gif"
            await asyncio.to_thread(merge_overlay, self.stash_img_path, overlay_path, merged_path)
    
            file = discord.File(merged_path, filename="merged_raid.gif")
    
            phase_titles = ["🔸 Phase 1", "🔸 Phase 2", "🌟 Final Phase"]
            embed = discord.Embed()
            embed.title = f"{self.visuals['emoji']} {self.target.display_name}'s Fortified Lab — {phase_titles[i]}"
            embed.description = f"""```\n{self.stash_visual}\n```"""
    
            if hit:
                embed.description += "\n\n✅ Attack successful!"
            else:
                consumed_txt = "(Consumed x1)" if consumed else "(Not consumed)"
                embed.description += f"\n\n💥 {rtype} triggered — attack blocked {consumed_txt}"
    
            embed.set_image(url="attachment://merged_raid.gif")
    
            self.phase += 1
            print(f"📊 Phase {i+1} completed. Hit={hit} | Trigger={rtype} | Consumed={consumed}")
    
            new_view = RaidView(
                self.ctx, self.attacker, self.defender, self.visuals,
                self.reinforcements, self.stash_visual, self.stash_img_path,
                self.is_test_mode, phase=self.phase, target=self.target
            )
            new_view.results = self.results.copy()
            new_view.triggered = self.triggered.copy()
            new_view.message = self.message
    
            if self.message:
                await self.message.edit(embed=embed, attachments=[file], view=new_view)
            else:
                self.message = await interaction.edit_original_response(embed=embed, attachments=[file], view=new_view)
    
        elif self.phase == 3:
            # Final results logic
            self.success = self.results.count(True) >= 2
            self.clear_items()
            self.add_item(CloseButton())
    
            dummy_embed = interaction.message.embeds[0] if interaction.message and interaction.message.embeds else discord.Embed()
            await self.finalize_results(dummy_embed)
    
            final_overlay = "victory.gif" if self.success else "miss.gif"
            final_path = f"temp/final_overlay_{self.attacker_id}.gif"
            await asyncio.to_thread(merge_overlay, self.stash_img_path, f"assets/overlays/{final_overlay}", final_path)
            file = discord.File(final_path, filename="final_overlay.gif")
    
            result_title = "🏆 Raid Concluded — Success!" if self.success else "❌ Raid Concluded — Failed"
            embed = discord.Embed(
                title=f"{self.visuals['emoji']} {self.target.display_name}'s Fortified Lab — {result_title}",
                description=f"""```\n{self.stash_visual}\n```""",
                color=discord.Color.green() if self.success else discord.Color.red()
            )
    
            summary = []
    
            if self.stolen_items:
                summary.append(f"🎒 Items stolen: {', '.join(self.stolen_items)}")
            if self.stolen_coins:
                summary.append(f"💰 Coins stolen: {self.stolen_coins}")
            if self.prestige_earned:
                summary.append(f"🏅 Prestige gained: {self.prestige_earned}")
            if not self.success:
                summary.append(f"💸 Lost **{self.coin_loss} coins** during the failed raid.")
    
            embed.add_field(name="🏁 Raid Summary", value="\n".join(summary) if summary else "No rewards gained.", inline=False)
            embed.set_image(url="attachment://final_overlay.gif")
    
            self.phase += 1
            if self.message:
                await self.message.edit(embed=embed, attachments=[file], view=self)
            else:
                await interaction.edit_original_response(embed=embed, attachments=[file], view=self)

# --------------------------  /raid Command  ------------------------------ #
class Raid(commands.Cog):
    def __init__(self, bot): self.bot = bot

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
            view.message = initial_msg

        if attacker_id == defender_id:
            return await interaction.followup.send("❌ You can’t raid yourself.", ephemeral=True)

        cooldowns = await load_file(COOLDOWN_FILE) or {}
        if defender_id in cooldowns.get(attacker_id, {}):
            last = datetime.fromisoformat(cooldowns[attacker_id][defender_id])
            if now - last < timedelta(hours=24):
                wait = timedelta(hours=24) - (now - last)
                return await interaction.followup.send(
                    f"⏳ Wait **{wait.seconds//3600}h** before raiding this player again.",
                    ephemeral=True)

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
            title=f"{visuals['emoji']} {target.display_name}'s Fortified Lab",
            description=f"""```\n{stash_visual}\n```""",
            color=visuals["color"]
        ).set_image(url="attachment://raid_stash.png")

        view = RaidView(interaction, attacker, defender, visuals, reinforcements,
                        stash_visual, stash_img_path, is_test, target=target)

        initial_msg = await interaction.followup.send(embed=embed, file=file, view=view, ephemeral=True)
        view.message = initial_msg  # ✅ Ensures attack_phase can later update this

# ---------------------------  Cog Setup  --------------------------------- #
async def setup(bot): await bot.add_cog(Raid(bot))
