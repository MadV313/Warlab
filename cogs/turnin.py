# cogs/turnin.py — Persistent Turn-In system with admin confirm DM + Railway file routing

import discord
from discord.ext import commands
from discord import app_commands
from utils.storageClient import load_file, save_file  # ✅ Use persistent storage functions
from utils.prestigeUtils import get_prestige_rank, get_prestige_progress
from datetime import datetime
import traceback
import asyncio  # (if not already imported)

USER_DATA = "user_profiles.json"  # ✅ Remove "data/" path prefix
TURNIN_LOG = "turnin_log.json"    # ✅ Remove "logs/" path prefix
TRADER_ORDERS_CHANNEL_ID = 1367583463775146167
ADMIN_ROLE_IDS = ["1173049392371085392", "1184921037830373468"]

REWARD_VALUES = {
    "base_prestige": 50,
    "tactical_bonus": 100,
    "coin_enabled": True,
    "coin_bonus": 25
}

TURNIN_ELIGIBLE = [
    "Mlock", "M4", "Mosin", "USG45", "BK-133",
    "Improvised Explosive Device", "Claymore", "Flashbang", "Frag Grenade",
    "Combat Outfit", "Tactical Outfit", "NBC Suit", "Humvee"
]

class TurnInButton(discord.ui.Button):
    def __init__(self, item_name: str, user_id: str):
        super().__init__(label=f"Turn In: {item_name}", style=discord.ButtonStyle.success)
        self.item_name = item_name.strip()
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("⚠️ That button isn’t for you.", ephemeral=True)
            return

        try:
            profiles = await load_file(USER_DATA) or {}
            logs = await load_file(TURNIN_LOG) or {}

            user_data = profiles.get(self.user_id)
            if not user_data:
                return await interaction.response.send_message("❌ No profile found.", ephemeral=True)

            crafted_list = [x.strip() for x in user_data.get("crafted", [])]
            if self.item_name not in crafted_list or self.item_name not in TURNIN_ELIGIBLE:
                return await interaction.response.send_message("❌ This item is not eligible or has already been turned in.", ephemeral=True)

            prestige = REWARD_VALUES["base_prestige"]
            if "Tactical" in self.item_name:
                prestige += REWARD_VALUES["tactical_bonus"]
            coins = REWARD_VALUES["coin_bonus"] if REWARD_VALUES["coin_enabled"] else 0

            user_data["crafted"].remove(self.item_name)
            user_data.setdefault("crafted_log", []).append(self.item_name)
            user_data["prestige"] += prestige
            user_data["coins"] += coins
            user_data["turnins_completed"] = user_data.get("turnins_completed", 0) + 1

            if self.item_name in user_data.get("stash", []):
                user_data["stash"].remove(self.item_name)

            logs.setdefault(self.user_id, []).append({
                "item": self.item_name,
                "reward_prestige": prestige,
                "reward_coins": coins,
                "timestamp": datetime.utcnow().isoformat()
            })

            await save_file(USER_DATA, profiles)
            await save_file(TURNIN_LOG, logs)

            success_embed = discord.Embed(
                title="✅ Item Turned In",
                description=(f"**{self.item_name}** submitted! Please stand by for further rewards.\n\n"
                             f"+ 🧠 `{prestige}` Prestige\n"
                             f"+ 💰 `{coins}` Coins"),
                color=0x00FF7F
            )
            await interaction.response.edit_message(embed=success_embed, view=None)

            try:
                channel = interaction.client.get_channel(TRADER_ORDERS_CHANNEL_ID)
                if channel:
                    admin_embed = discord.Embed(
                        title="🔧 Craft Turn-In",
                        description=(f"🧑 Player: <@{self.user_id}>\n"
                                     f"📦 Item: {self.item_name}\n"
                                     f"🧠 Prestige: {prestige}\n"
                                     f"💰 Coins: {coins if coins else 'None'}"),
                        color=0xF1C40F
                    )
                    admin_embed.set_footer(text="Please click the button below when the reward is ready.")
                    await channel.send(embed=admin_embed, view=RewardConfirmView(self.user_id, self.item_name))
            except Exception:
                print("❌ [Admin Ping Error]\n" + traceback.format_exc())

        except Exception:
            print("❌ [TurnInButton Error]\n" + traceback.format_exc())
            await interaction.followup.send("❌ Something broke while processing your turn-in. Please ping an admin.", ephemeral=True)

class RewardConfirmView(discord.ui.View):
    def __init__(self, player_id, item_name):
        super().__init__(timeout=86400)
        self.add_item(ConfirmRewardButton(player_id, item_name))

class ConfirmRewardButton(discord.ui.Button):
    def __init__(self, player_id, item_name):
        super().__init__(label="✅ Confirm Reward Ready", style=discord.ButtonStyle.success)
        self.player_id = player_id
        self.item_name = item_name

    async def callback(self, interaction: discord.Interaction):
        if not any(str(role.id) in ADMIN_ROLE_IDS for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You are not authorized to confirm rewards.", ephemeral=True)

        await interaction.message.edit(content=f"✅ Confirmed by {interaction.user.mention}", view=None)

        try:
            profiles = await load_file(USER_DATA) or {}
            player_data = profiles.get(self.player_id, {})

            prestige_total = player_data.get("prestige", 0)
            crafted_total = len(player_data.get("crafted_log", []))
            rank = get_prestige_rank(prestige_total)
            progress_data = get_prestige_progress(prestige_total)

            current = progress_data["points"]
            current_threshold = progress_data["current_threshold"]
            next_threshold = progress_data["next_threshold"]
            progress = (current - current_threshold) / (next_threshold - current_threshold) if next_threshold else 1.0
            bar = f"[{'█' * int(progress * 10):<10}] {int(progress * 100)}%"

            user = await interaction.client.fetch_user(int(self.player_id))
            if user:
                await user.send(
                    f"🎉 **Your reward has been confirmed! Please make your way to Sobotka Trader to receive your new:**\n\n"
                    f"🔧 **Item Turned In:** {self.item_name}\n"
                    f"📦 **Total Builds Completed:** `{crafted_total}`\n"
                    f"🧠 **Current Prestige:** `{prestige_total}` • *{rank}*\n"
                    f"📊 **Progress to Next Rank:** {bar}\n\n"
                    f"🫡 Stay frosty, Survivor — your legend is growing!"
                )
        except Exception as e:
            print(f"⚠️ [RewardConfirmButton Error] {e}")

        await interaction.response.defer()

class TurnIn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="turnin", description="Submit a crafted item for rewards")
    async def turnin(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        user_data = profiles.get(user_id)

        if not user_data:
            return await interaction.response.send_message("❌ You don’t have a profile yet. Use `/register` first.", ephemeral=True)

        crafted = [x.strip() for x in user_data.get("crafted", [])]
        eligible = [item for item in crafted if item in TURNIN_ELIGIBLE]

        if not eligible:
            return await interaction.response.send_message("❌ No eligible crafted items to turn in. Use `/craft` first.", ephemeral=True)

        embed = discord.Embed(
            title="📦 Crafted Items Ready",
            description="Click a button to submit an item for rewards:",
            color=0x3498DB
        )

        view = discord.ui.View(timeout=86400)
        for item in eligible[:10]:
            view.add_item(TurnInButton(item, user_id))

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(TurnIn(bot))
