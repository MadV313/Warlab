# cogs/turnin.py — Updated Turn-In system with correct stash consumption tracking, prestige display, and admin logging

import discord
from discord.ext import commands
from discord import app_commands
from utils.fileIO import load_file, save_file
from utils.prestigeUtils import get_prestige_rank, get_prestige_progress
from datetime import datetime
import traceback
import os

USER_DATA   = "data/user_profiles.json"
TURNIN_LOG  = "logs/turnin_log.json"
TAXMAN_LOG  = "logs/taxman_log.json"
RECIPE_DATA = "data/item_recipes.json"
CONFIRMATION_LOG = "logs/confirmations.json"
TRADER_ORDERS_CHANNEL_ID = 1367583463775146167
ECONOMY_CHANNEL_ID = 1367583463775146167
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
            recipes = await load_file(RECIPE_DATA) or {}
            logs = await load_file(TURNIN_LOG) or {}
            taxlog = await load_file(TAXMAN_LOG) or {}

            user_data = profiles.get(self.user_id)
            if not user_data:
                return await interaction.response.send_message("❌ No profile found.", ephemeral=True)

            crafted_list = user_data.get("crafted", [])
            if self.item_name not in crafted_list or self.item_name not in TURNIN_ELIGIBLE:
                return await interaction.response.send_message(
                    "❌ This item is not eligible or was already turned in.", ephemeral=True)

            recipe_key = self.item_name.lower()
            recipe = recipes.get(recipe_key)
            if not recipe:
                return await interaction.response.send_message("❌ Recipe not found.", ephemeral=True)

            used_parts = recipe.get("requirements", {}).copy()
            for part, qty in recipe.get("optional", {}).items():
                if user_data.get("stash", []).count(part) >= qty:
                    used_parts[part] = used_parts.get(part, 0) + qty
                    for _ in range(qty):
                        user_data["stash"].remove(part)

            for part, qty in recipe.get("requirements", {}).items():
                for _ in range(qty):
                    user_data["stash"].remove(part)

            prestige = REWARD_VALUES["base_prestige"]
            if "Tactical" in self.item_name:
                prestige += REWARD_VALUES["tactical_bonus"]
            coins = REWARD_VALUES["coin_bonus"] if REWARD_VALUES["coin_enabled"] else 0

            user_data["crafted"].remove(self.item_name)
            user_data.setdefault("crafted_log", []).append(self.item_name)
            user_data["prestige"] += prestige
            user_data["coins"] += coins
            user_data["turnins_completed"] = user_data.get("turnins_completed", 0) + 1

            logs.setdefault(self.user_id, []).append({
                "item": self.item_name,
                "reward_prestige": prestige,
                "reward_coins": coins,
                "parts_consumed": used_parts,
                "timestamp": datetime.utcnow().isoformat()
            })

            taxlog.setdefault(self.user_id, 0)
            taxlog[self.user_id] += prestige

            await save_file(USER_DATA, profiles)
            await save_file(TURNIN_LOG, logs)
            await save_file(TAXMAN_LOG, taxlog)

            embed = discord.Embed(
                title="✅ Item Turned In",
                description=(f"**{self.item_name}** submitted!\n\n"
                             f"+ 🧠 `{prestige}` Prestige\n"
                             f"+ 💰 `{coins}` Coins"),
                color=0x00FF7F
            )
            current_rank = get_prestige_rank(user_data["prestige"])
            progress = get_prestige_progress(user_data["prestige"])
            embed.add_field(name="Current Prestige", value=f"{user_data['prestige']} • *{current_rank}*", inline=True)
            embed.add_field(name="Progress to Next", value=f"{progress}", inline=True)
            await interaction.response.edit_message(embed=embed, view=None)

            try:
                channel = interaction.client.get_channel(TRADER_ORDERS_CHANNEL_ID)
                if channel:
                    part_lines = [f"{qty}x {part}" for part, qty in used_parts.items()]
                    admin_embed = discord.Embed(
                        title="🔧 Craft Turn-In",
                        description=(f"🧑 Player: <@{self.user_id}>\n"
                                     f"📦 Item: {self.item_name}\n"
                                     f"🧠 Prestige: {prestige}\n"
                                     f"💰 Coins: {coins if coins else 'None'}"),
                        color=0xF1C40F
                    )
                    admin_embed.add_field(name="Parts Consumed", value="\n".join(part_lines), inline=False)
                    await channel.send(embed=admin_embed, view=RewardConfirmView(self.user_id, self.item_name))
            except Exception:
                print("❌ [Admin Ping Error]\n" + traceback.format_exc())

        except Exception:
            print("❌ [TurnInButton Error]\n" + traceback.format_exc())
            await interaction.followup.send(
                "❌ Something broke while processing your turn-in. Please ping an admin.", ephemeral=True)


class RewardConfirmView(discord.ui.View):
    def __init__(self, player_id, item_name):
        super().__init__(timeout=None)
        self.add_item(ConfirmRewardButton(player_id, item_name))


class ConfirmRewardButton(discord.ui.Button):
    def __init__(self, player_id, item_name):
        super().__init__(label="✅ Confirm Reward", style=discord.ButtonStyle.success)
        self.player_id = player_id
        self.item_name = item_name

    async def callback(self, interaction: discord.Interaction):
        if not any(str(role.id) in ADMIN_ROLE_IDS for role in interaction.user.roles):
            await interaction.response.send_message("❌ You are not authorized to confirm rewards.", ephemeral=True)
            return

        profiles = await load_file(USER_DATA) or {}
        player = profiles.get(self.player_id)
        if not player:
            return await interaction.response.send_message("❌ Player profile not found.", ephemeral=True)

        prestige = REWARD_VALUES["base_prestige"]
        if "Tactical" in self.item_name:
            prestige += REWARD_VALUES["tactical_bonus"]

        await interaction.message.edit(content=f"✅ Reward confirmed by <@{interaction.user.id}>", view=None)

        economy_channel = interaction.client.get_channel(ECONOMY_CHANNEL_ID)
        if economy_channel:
            await economy_channel.send(
                f"💰 <@{self.player_id}> has received **{prestige} prestige** for turning in **{self.item_name}**."
            )

        confirmations = await load_file(CONFIRMATION_LOG) or []
        confirmations.append({
            "confirmed_by": str(interaction.user),
            "confirmed_by_id": str(interaction.user.id),
            "target_user_id": self.player_id,
            "amount": prestige,
            "reason": f"Turn-In: {self.item_name}",
            "timestamp": datetime.utcnow().isoformat()
        })
        await save_file(CONFIRMATION_LOG, confirmations)

        taxlog = await load_file(TAXMAN_LOG) or {}
        admin_id_str = str(interaction.user.id)
        taxlog[admin_id_str] = taxlog.get(admin_id_str, 0) + 1
        await save_file(TAXMAN_LOG, taxlog)

        await interaction.response.send_message("✅ Confirmation logged.", ephemeral=True)


class TurnIn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="turnin", description="View your eligible crafted items to turn in for rewards.")
    async def turnin(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        user_data = profiles.get(user_id)

        if not user_data or not user_data.get("crafted"):
            return await interaction.response.send_message("❌ You have no crafted items to turn in.", ephemeral=True)

        eligible_items = [item for item in user_data["crafted"] if item in TURNIN_ELIGIBLE]
        if not eligible_items:
            return await interaction.response.send_message("❌ No eligible turn-ins found.", ephemeral=True)

        embed = discord.Embed(
            title="🧾 Available Turn-Ins",
            description="Click a button below to turn in one of your crafted items.",
            color=0x3498DB
        )
        view = discord.ui.View(timeout=60)
        for item in eligible_items[:5]:
            view.add_item(TurnInButton(item, user_id))

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(TurnIn(bot))
