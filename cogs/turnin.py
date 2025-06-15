# cogs/turnin.py — Submit crafted items for rewards (dropdown-only)

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

# ──────────────────────────────────────────────────────────────────

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
                f"🎉 Your crafted item reward has been confirmed and is now available for pickup at the trader!\n\n"
                f"🔧 Great job, {self.player_name}!\n"
                f"📦 **Total builds completed**: `{total_turnins}`\n"
                f"🧬 **Current Prestige**: `{prestige}` ({rank})\n"
                f"📊 **Progress**: {progress}% toward next rank"
            )

        await interaction.response.defer()

# ──────────────────────────────────────────────────────────────────

class RewardConfirmView(discord.ui.View):
    def __init__(self, player_id, player_name):
        super().__init__(timeout=None)
        self.add_item(ConfirmRewardButton(player_id, player_name))

# ──────────────────────────────────────────────────────────────────

class TurnInDropdown(discord.ui.Select):
    def __init__(self, user_id, crafted_items):
        self.user_id = user_id
        options = [discord.SelectOption(label=item, value=item) for item in crafted_items[:24]]
        options.insert(0, discord.SelectOption(label="All", value="all", description="Submit all crafted items"))
        super().__init__(placeholder="Select a crafted item to turn in...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("⚠️ You can’t use another player’s menu.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        user_id = self.user_id
        item = self.values[0].lower()

        profiles = await load_file(USER_DATA) or {}
        logs = await load_file(TURNIN_LOG) or {}
        user_data = profiles[user_id]

        crafted_items = user_data.get("crafted", [])
        is_bulk = item == "all"
        items_to_turnin = crafted_items[:] if is_bulk else [item]

        reward_summary = []
        total_prestige = 0
        total_coins = 0
        confirmed_items = []

        for item_name in items_to_turnin:
            if item_name not in user_data["crafted"]:
                continue

            prestige = REWARD_VALUES["base_prestige"]
            if "Tactical" in item_name:
                prestige += REWARD_VALUES["tactical_bonus"]

            coins = REWARD_VALUES["coin_bonus"] if REWARD_VALUES["coin_enabled"] else 0
            total_prestige += prestige
            total_coins += coins

            user_data["crafted"].remove(item_name)
            user_data.setdefault("crafted_log", []).append(item_name)
            logs.setdefault(user_id, []).append({
                "item": item_name,
                "reward_prestige": prestige,
                "reward_coins": coins,
                "timestamp": datetime.utcnow().isoformat()
            })

            reward_summary.append(f"• **{item_name}** → 🧬 {prestige} Prestige" + (f" + 💰 {coins} Coins" if coins else ""))
            confirmed_items.append(item_name)

        if not reward_summary:
            await interaction.followup.send("❌ No valid crafted items found to turn in.", ephemeral=True)
            return

        user_data["prestige"] += total_prestige
        user_data["coins"] += total_coins
        profiles[user_id] = user_data

        await save_file(USER_DATA, profiles)
        await save_file(TURNIN_LOG, logs)

        embed = discord.Embed(
            title="📦 Items Turned In",
            description="\n".join(reward_summary),
            color=0x00ff00
        )
        embed.set_footer(text=f"Total: {total_prestige} Prestige" + (f", {total_coins} Coins" if total_coins else ""))
        await interaction.followup.send(embed=embed, ephemeral=True)

        # Admin payout
        admin_embed = discord.Embed(
            title="🔧 Craft Turn-In",
            description=(
                f"🧍 Player: <@{user_id}>\n"
                f"📦 Items: {', '.join(confirmed_items)}\n"
                f"🧬 Prestige: {total_prestige}\n"
                f"💰 Coins: {total_coins if total_coins else 'None'}\n\n"
                "✅ Please confirm this message with the button below when the reward is ready."
            ),
            color=0xf1c40f
        )
        view = RewardConfirmView(user_id, interaction.user.name)
        channel = interaction.client.get_channel(TRADER_ORDERS_CHANNEL_ID)
        if channel:
            await channel.send(embed=admin_embed, view=view)

# ──────────────────────────────────────────────────────────────────

class TurnInView(discord.ui.View):
    def __init__(self, user_id, crafted_items):
        super().__init__(timeout=60)
        self.add_item(TurnInDropdown(user_id, crafted_items))

# ──────────────────────────────────────────────────────────────────

class TurnIn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="turnin", description="Submit a crafted item for rewards")
    async def turnin(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        user_data = profiles.get(user_id)

        if not user_data:
            await interaction.followup.send("❌ You don’t have a profile yet. Please use `/register` first.", ephemeral=True)
            return

        crafted = user_data.get("crafted", [])
        if not crafted:
            await interaction.followup.send("❌ You have no crafted items to turn in. Try using `/craft` first.", ephemeral=True)
            return

        await interaction.followup.send("📦 Select a crafted item to submit for rewards:", view=TurnInView(user_id, crafted), ephemeral=True)

async def setup(bot):
    await bot.add_cog(TurnIn(bot))
