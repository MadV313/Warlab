# cogs/turnin.py — Visual Turn-In UI with buttons (robust + counters + admin confirmation ping)

import discord
from discord.ext import commands
from discord import app_commands
from utils.fileIO import load_file, save_file
from utils.prestigeUtils import get_prestige_rank, get_prestige_progress
from datetime import datetime
import traceback

USER_DATA  = "data/user_profiles.json"
TURNIN_LOG = "logs/turnin_log.json"
TRADER_ORDERS_CHANNEL_ID = 1367583463775146167

REWARD_VALUES = {
    "base_prestige" : 50,
    "tactical_bonus": 100,
    "coin_enabled"  : True,
    "coin_bonus"    : 25
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
        self.user_id   = user_id

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("⚠️ That button isn’t for you.", ephemeral=True)
            return

        try:
            profiles = await load_file(USER_DATA) or {}
            logs     = await load_file(TURNIN_LOG) or {}
            user_data = profiles.get(self.user_id)

            crafted_list = [x.strip() for x in user_data.get("crafted", [])] if user_data else []

            if not user_data or self.item_name not in crafted_list or self.item_name not in TURNIN_ELIGIBLE:
                print(f"[❌ TurnIn DEBUG] Crafted List: {crafted_list}")
                print(f"[❌ TurnIn DEBUG] Requested Item: {self.item_name}")
                await interaction.response.send_message(
                    "❌ This item is no longer eligible or has already been turned in.",
                    ephemeral=True
                )
                return

            prestige = REWARD_VALUES["base_prestige"]
            if "Tactical" in self.item_name:
                prestige += REWARD_VALUES["tactical_bonus"]
            coins = REWARD_VALUES["coin_bonus"] if REWARD_VALUES["coin_enabled"] else 0

            user_data["crafted"].remove(self.item_name)
            user_data.setdefault("crafted_log", []).append(self.item_name)
            user_data["prestige"] += prestige
            user_data["coins"]    += coins
            user_data["turnins_completed"] = user_data.get("turnins_completed", 0) + 1

            if self.item_name in user_data.get("stash", []):
                user_data["stash"].remove(self.item_name)

            logs.setdefault(self.user_id, []).append({
                "item"           : self.item_name,
                "reward_prestige": prestige,
                "reward_coins"   : coins,
                "timestamp"      : datetime.utcnow().isoformat()
            })

            profiles[self.user_id] = user_data
            await save_file(USER_DATA,  profiles)
            await save_file(TURNIN_LOG, logs)

            success_embed = discord.Embed(
                title="✅ Item Turned In",
                description=(f"**{self.item_name}** submitted! Please stand by for further rewards!\n\n"
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
                                     f"📦 Item : {self.item_name}\n"
                                     f"🧠 Prestige: {prestige}\n"
                                     f"💰 Coins   : {coins if coins else 'None'}\n\n"
                                     "**Please click the button below when the reward is ready.**"),
                        color=0xF1C40F
                    )
                    await channel.send(embed=admin_embed,
                                       view=RewardConfirmView(self.user_id, self.item_name))
                else:
                    await interaction.followup.send(
                        "⚠️ Admin payout channel not found. Please alert staff.",
                        ephemeral=True
                    )
            except Exception:
                print("❌ [Admin Ping Error]\n" + traceback.format_exc())

        except Exception:
            print("❌ [TurnInButton Error]\n" + traceback.format_exc())
            await interaction.followup.send(
                "❌ Something broke while processing your turn-in — please ping an admin.",
                ephemeral=True
            )

class RewardConfirmView(discord.ui.View):
    def __init__(self, player_id: str, item_name: str):
        super().__init__(timeout=86400)
        self.add_item(ConfirmRewardButton(player_id, item_name))

class ConfirmRewardButton(discord.ui.Button):
    def __init__(self, player_id: str, item_name: str):
        super().__init__(label="Confirm Reward Ready", style=discord.ButtonStyle.success)
        self.player_id  = player_id
        self.item_name  = item_name

    async def callback(self, interaction: discord.Interaction):
        await interaction.message.edit(content=f"✅ Confirmed by {interaction.user.mention}", view=None)

        try:
            profiles = await load_file(USER_DATA) or {}
            profile  = profiles.get(self.player_id, {})

            prestige  = profile.get("prestige", 0)
            rank_name = get_prestige_rank(prestige)
            progress  = get_prestige_progress(prestige)
            total     = len(profile.get("crafted_log", []))

            player = interaction.client.get_user(int(self.player_id))
            if player:
                await player.send(
                    f"🎉 **Your reward has been confirmed! Please make your way to Sobotka Trader to receive your new:**\n\n"
                    f"🔧 **Item Turned In:** {self.item_name}\n"
                    f"📦 **Total Builds Completed:** `{total}`\n"
                    f"🧠 **Current Prestige:** `{prestige}` • *{rank_name}*\n"
                    f"📊 **Progress to Next Rank:** `{progress}`\n\n"
                    f"🫡 Stay frosty, Survivor — your legend is growing!"
                )

        except Exception:
            print("⚠️ [RewardConfirmButton Error]\n" + traceback.format_exc())

        await interaction.response.defer()

class TurnIn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="turnin", description="Submit a crafted item for rewards")
    async def turnin(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        profiles  = await load_file(USER_DATA) or {}
        user_data = profiles.get(user_id)

        if not user_data:
            await interaction.response.send_message(
                "❌ You don’t have a profile yet. Use `/register` first.",
                ephemeral=True
            )
            return

        crafted = [x.strip() for x in user_data.get("crafted", [])]
        eligible = [item for item in crafted if item in TURNIN_ELIGIBLE]

        if not eligible:
            await interaction.response.send_message(
                "❌ No eligible crafted items to turn in. Use `/craft` first.",
                ephemeral=True
            )
            return

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
