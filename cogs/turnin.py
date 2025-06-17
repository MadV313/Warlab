# cogs/turnin.py — Visual Turn-In UI with buttons (no dropdown)

import discord
from discord.ext import commands
from discord import app_commands
from utils.fileIO import load_file, save_file
from utils.prestigeUtils import get_prestige_rank, get_prestige_progress
from datetime import datetime

USER_DATA = "data/user_profiles.json"
TURNIN_LOG = "logs/turnin_log.json"
TRADER_ORDERS_CHANNEL_ID = 1367583463775146167

REWARD_VALUES = {
    "base_prestige": 50,
    "tactical_bonus": 100,
    "coin_enabled": True,
    "coin_bonus": 25
}

# Button for each crafted item
class TurnInButton(discord.ui.Button):
    def __init__(self, item_name, user_id):
        super().__init__(label=f"Turn In: {item_name}", style=discord.ButtonStyle.success)
        self.item_name = item_name
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("⚠️ This button isn't for you.", ephemeral=True)
            return

        profiles = await load_file(USER_DATA) or {}
        logs = await load_file(TURNIN_LOG) or {}
        user_data = profiles.get(str(self.user_id))

        if not user_data or self.item_name not in user_data.get("crafted", []):
            await interaction.response.send_message("❌ Item not found or already submitted.", ephemeral=True)
            return

        prestige = REWARD_VALUES["base_prestige"]
        if "Tactical" in self.item_name:
            prestige += REWARD_VALUES["tactical_bonus"]

        coins = REWARD_VALUES["coin_bonus"] if REWARD_VALUES["coin_enabled"] else 0

        user_data["crafted"].remove(self.item_name)
        user_data.setdefault("crafted_log", []).append(self.item_name)
        user_data["prestige"] += prestige
        user_data["coins"] += coins

        logs.setdefault(str(self.user_id), []).append({
            "item": self.item_name,
            "reward_prestige": prestige,
            "reward_coins": coins,
            "timestamp": datetime.utcnow().isoformat()
        })

        await save_file(USER_DATA, profiles)
        await save_file(TURNIN_LOG, logs)

        # Update embed UI
        embed = discord.Embed(
            title="📦 Item Turned In",
            description=f"You submitted **{self.item_name}**\n+ 🧠 `{prestige}` Prestige\n+ 💰 `{coins}` Coins",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=None)

        # Notify admin
        admin_embed = discord.Embed(
            title="🔧 Craft Turn-In",
            description=(
                f"🧑 Player: <@{self.user_id}>\n"
                f"📦 Item: {self.item_name}\n"
                f"🧠 Prestige: {prestige}\n"
                f"💰 Coins: {coins if coins else 'None'}\n\n"
                "✅ Please confirm this message with the button below when the reward is ready."
            ),
            color=0xf1c40f
        )
        view = RewardConfirmView(self.user_id, interaction.user.name)
        channel = interaction.client.get_channel(TRADER_ORDERS_CHANNEL_ID)
        if channel:
            await channel.send(embed=admin_embed, view=view)

# Admin confirm view
class RewardConfirmView(discord.ui.View):
    def __init__(self, player_id, player_name):
        super().__init__(timeout=None)
        self.add_item(ConfirmRewardButton(player_id, player_name))

class ConfirmRewardButton(discord.ui.Button):
    def __init__(self, player_id, player_name):
        super().__init__(label="Confirm Reward Ready", style=discord.ButtonStyle.success)
        self.player_id = player_id
        self.player_name = player_name

    async def callback(self, interaction: discord.Interaction):
        await interaction.message.edit(content=f"✅ Order confirmed by {interaction.user.mention}", view=None)
        user = interaction.client.get_user(int(self.player_id))

        profiles = await load_file(USER_DATA) or {}
        profile = profiles.get(self.player_id, {})
        prestige = profile.get("prestige", 0)
        rank = get_prestige_rank(prestige)
        progress = get_prestige_progress(prestige)
        total_turnins = len(profile.get("crafted_log", []))

        if user:
            await user.send(
                f"🎉 Your crafted item reward has been confirmed and is now available for pickup!\n\n"
                f"🔧 Great job, {self.player_name}!\n"
                f"📦 **Total builds completed**: `{total_turnins}`\n"
                f"🧠 **Current Prestige**: `{prestige}` ({rank})\n"
                f"📊 **Progress**: {progress}% toward next rank"
            )
        await interaction.response.defer()

# Command setup
class TurnIn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="turnin", description="Submit a crafted item for rewards")
    async def turnin(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        user_data = profiles.get(user_id)

        if not user_data:
            await interaction.response.send_message("❌ You don’t have a profile yet. Please use `/register` first.", ephemeral=True)
            return

        crafted = user_data.get("crafted", [])
        if not crafted:
            await interaction.response.send_message("❌ You have no crafted items to turn in. Try using `/craft` first.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📦 Crafted Items Ready to Turn In",
            description="Click a button below to submit one item for Prestige + Coins:",
            color=0x3498db
        )

        view = discord.ui.View(timeout=120)
        for item in crafted[:10]:
            view.add_item(TurnInButton(item, user_id))

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(TurnIn(bot))
