# cogs/turnin.py — Persistent Turn-In system with admin confirm DM + Railway file routing

import discord
from discord.ext import commands
from discord import app_commands
from utils.storageClient import load_file, save_file
from utils.prestigeUtils import get_prestige_rank, get_prestige_progress
from datetime import datetime
import traceback
import asyncio
from collections import Counter
from cogs.rank import RANK_TITLES 

USER_DATA = "data/user_profiles.json"
TURNIN_LOG = "logs/turnin_log.json"
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

            stash = user_data.get("stash", [])
            crafted_entries = user_data.get("crafted", [])
            crafted_entry = next((c for c in crafted_entries if isinstance(c, dict) and c.get("item") == self.item_name), None)

            if self.item_name not in stash or not crafted_entry:
                return await interaction.response.send_message("❌ This item is not eligible or not in your stash.", ephemeral=True)

            prestige = REWARD_VALUES["base_prestige"]
            if "Tactical" in self.item_name:
                prestige += REWARD_VALUES["tactical_bonus"]
            coins = REWARD_VALUES["coin_bonus"] if REWARD_VALUES["coin_enabled"] else 0

            # Remove from stash and crafted[]
            user_data["stash"].remove(self.item_name)
            user_data["crafted"].remove(crafted_entry)

            user_data.setdefault("crafted_log", []).append(self.item_name)
            user_data["prestige"] += prestige
            user_data["coins"] += coins
            user_data["turnins_completed"] = user_data.get("turnins_completed", 0) + 1

            logs.setdefault(self.user_id, []).append({
                "item": self.item_name,
                "reward_prestige": prestige,
                "reward_coins": coins,
                "timestamp": datetime.utcnow().isoformat()
            })

            await save_file(USER_DATA, profiles)
            await save_file(TURNIN_LOG, logs)

            optional_bonus = "\n• " + "\n• ".join(crafted_entry.get("optional", [])) if crafted_entry.get("optional") else "None"

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
                                     f"💰 Coins: {coins if coins else 'None'}\n"
                                     f"🧩 Optional Parts: {optional_bonus}"),
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

            prestige_points = player_data.get("prestige_points", 0)
            crafted_total = len(player_data.get("crafted_log", []))
            progress_data = get_prestige_progress(prestige_points)
            current_tier = progress_data["current_rank"]
            next_threshold = progress_data["next_threshold"]
            rank_title = RANK_TITLES.get(current_tier, "Unknown")
            
            # Optional: store prestige for consistency with /rank
            player_data["prestige"] = current_tier
            
            # Build progress bar
            if next_threshold:
                bar = f"[{'█' * int((progress_data['points'] / next_threshold) * 10):<10}] {int((progress_data['points'] / next_threshold) * 100)}%"
            else:
                bar = "[██████████] MAX"
            
            # Send DM to player
            user = await interaction.client.fetch_user(int(self.player_id))
            if user:
                await user.send(
                    f"🎉 **Your reward has been confirmed! Please make your way to Sobotka Trader to receive your new:**\n\n"
                    f"🔧 **Item Turned In:** {self.item_name}\n"
                    f"📦 **Total Builds Completed:** `{crafted_total}`\n"
                    f"🧠 **Current Prestige:** `{prestige_points}` • *{rank_title}*\n"
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

        stash_counter = Counter(user_data.get("stash", []))
        crafted_list = user_data.get("crafted", [])
        crafted_items = {entry["item"] for entry in crafted_list if isinstance(entry, dict)}
        eligible = [item for item in TURNIN_ELIGIBLE if stash_counter.get(item, 0) > 0 and item in crafted_items]

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
