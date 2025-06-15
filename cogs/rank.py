import discord
from discord.ext import commands
from discord import app_commands
import json
import random
from datetime import datetime

USER_DATA_FILE = "data/user_profiles.json"
WARLAB_CHANNEL_ID = 1382187883590455296  # 🔒 Hardcoded Warlab channel

RANK_TITLES = {
    0: "Unranked Survivor",
    1: "Field Engineer",
    2: "Weapon Tech",
    3: "Shadow Engineer",
    4: "Warlab Veteran",
    5: "Legendary Craftsman"
}

SPECIAL_REWARDS = {
    1: {"title": "⚔️ Weaponsmith Elite", "color": 0x3cb4fc},
    2: {"title": "⚒️ Scavenger Elite", "color": 0x88e0a0},
    3: {"title": "☠️ Raider Elite", "color": 0x880808}
}

PRESTIGE_ROLES = {
    1: 1184964035863650395,
    2: 1184963951746879638,
    3: 1184964276776091741,
    4: 1184964646055190558,
    5: 1184964764313583657
}

BOOST_CATALOG = {
    "special_class": {"label": "Special Class", "cost": 1000},
    "loot_boost": {"label": "Daily Loot Boost", "cost": 500},
    "coin_doubler": {"label": "Coin Doubler for Tasks", "cost": 0, "note": "Rare Drop"}
}

class RankView(discord.ui.View):
    def __init__(self, user_id, user_data, update_callback):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.user_data = user_data
        self.update_callback = update_callback

        can_prestige = self.user_data.get("builds_completed", 0) >= 5
        self.prestige_button.disabled = not can_prestige

    @discord.ui.button(label="🧬 Prestige", style=discord.ButtonStyle.danger, custom_id="prestige_button")
    async def prestige_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ You can’t use another player’s UI.", ephemeral=True)
            return

        builds = self.user_data.get("builds_completed", 0)
        if builds < 5:
            await interaction.response.send_message("🔒 You need at least 5 full builds to prestige.", ephemeral=True)
            return

        rolled_id = random.choice(list(SPECIAL_REWARDS.keys()))
        self.user_data["special_class"] = rolled_id
        self.user_data["prestige"] = self.user_data.get("prestige", 0) + 1
        self.user_data["rank_level"] = self.user_data["prestige"]  # 🔄 Sync rank with prestige
        self.user_data["builds_completed"] = 0
        self.user_data["stash"] = []
        self.user_data["boosts"] = {}
        self.update_callback(self.user_id, self.user_data)

        reward = SPECIAL_REWARDS[rolled_id]
        await interaction.response.send_message(
            f"🌟 Prestige successful! You rolled: **{reward['title']}**. Cosmetic perks unlocked.",
            ephemeral=True
        )

        prestige_level = self.user_data["prestige"]
        warlab_channel = interaction.client.get_channel(WARLAB_CHANNEL_ID)
        if warlab_channel:
            embed = discord.Embed(
                title=f"🧬 Prestige Unlocked!",
                description=(
                    f"{interaction.user.mention} has reached **Prestige Level {prestige_level}**!\n"
                    f"🎖 Prestige Class: **{reward['title']}**\n\n"
                    f"🎲 Use `/rollblueprint` to try for a new schematic!"
                ),
                color=reward["color"],
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text="Warlab Protocol: Prestige Activated")
            await warlab_channel.send(embed=embed)

        guild = interaction.guild
        role_id = PRESTIGE_ROLES.get(prestige_level)
        if guild and role_id:
            roles_to_remove = [guild.get_role(rid) for lvl, rid in PRESTIGE_ROLES.items() if lvl != prestige_level]
            for r in roles_to_remove:
                if r and r in interaction.user.roles:
                    await interaction.user.remove_roles(r, reason="Old prestige role removed")
            new_role = guild.get_role(role_id)
            if new_role:
                await interaction.user.add_roles(new_role, reason="Prestige reward role")

    @discord.ui.button(label="⚡ Buy Boost", style=discord.ButtonStyle.primary, custom_id="buyboost_button")
    async def buy_boost_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ You can’t use another player’s UI.", ephemeral=True)
            return

        owned = self.user_data.get("boosts", {})
        coins = self.user_data.get("coins", 0)

        options = []
        for key, boost in BOOST_CATALOG.items():
            if owned.get(key, False):
                continue
            label = boost["label"]
            if boost["cost"] > 0:
                options.append(discord.SelectOption(label=f"{label} — {boost['cost']} coins", value=key))
            else:
                note = boost.get("note", "Special")
                options.append(discord.SelectOption(label=f"{label} — {note}", value=key, description="Cannot buy unless dropped"))

        if not options:
            await interaction.response.send_message("✅ You already own all available boosts.", ephemeral=True)
            return

        await interaction.response.send_message(
            "Choose a boost to purchase:",
            view=BoostDropdown(self.user_id, self.user_data, self.update_callback, options),
            ephemeral=True
        )

class BoostDropdown(discord.ui.View):
    def __init__(self, user_id, user_data, update_callback, options):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.user_data = user_data
        self.update_callback = update_callback

        self.select = discord.ui.Select(
            placeholder="Select a boost...",
            options=options,
            custom_id="boost_select"
        )
        self.select.callback = self.process_boost
        self.add_item(self.select)

    async def process_boost(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This dropdown isn’t yours.", ephemeral=True)
            return

        selection = self.select.values[0]
        boost = BOOST_CATALOG.get(selection)
        coins = self.user_data.get("coins", 0)

        if boost["cost"] > coins:
            await interaction.response.send_message(f"❌ You need {boost['cost']} coins to buy this boost.", ephemeral=True)
            return

        self.user_data["coins"] -= boost["cost"]
        self.user_data.setdefault("boosts", {})[selection] = True
        self.update_callback(self.user_id, self.user_data)

        await interaction.response.send_message(f"✅ Boost unlocked: **{boost['label']}**!", ephemeral=True)

class Rank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_profiles(self):
        try:
            with open(USER_DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return {}

    def save_profiles(self, data):
        with open(USER_DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def update_user(self, uid, data):
        all_data = self.load_profiles()
        all_data[uid] = data
        self.save_profiles(all_data)

    def determine_special_reward(self, user_data):
        all_blueprints = user_data.get("blueprints", {})
        scavenges = user_data.get("scavenges", 0)
        raids = user_data.get("successful_raids", 0)

        if all_blueprints and all(all_blueprints.values()):
            return SPECIAL_REWARDS[1]
        elif scavenges >= 100:
            return SPECIAL_REWARDS[2]
        elif raids >= 25:
            return SPECIAL_REWARDS[3]
        return None

    @app_commands.command(name="rank", description="View your current rank, prestige, and buy upgrades.")
    async def rank(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        profiles = self.load_profiles()
        user = profiles.get(uid)

        if not user:
            await interaction.response.send_message("❌ You don’t have any profile data yet.", ephemeral=True)
            return

        prestige = user.get("prestige", 0)
        level = user.get("rank_level", 0)
        coins = user.get("coins", 0)
        builds = user.get("builds_completed", 0)
        turnins = user.get("turnins", 0)
        boosts = user.get("boosts", {})
        rolled_class_id = user.get("special_class")

        special_reward = self.determine_special_reward(user)
        embed_color = special_reward["color"] if special_reward else (
            SPECIAL_REWARDS.get(rolled_class_id, {}).get("color", 0x88e0ef)
        )

        embed = discord.Embed(title=f"🏅 {interaction.user.display_name}'s Rank", color=embed_color)
        embed.add_field(name="🎖️ Rank Title", value=RANK_TITLES.get(level, "???"), inline=False)
        if special_reward:
            embed.add_field(name="🧬 Prestige Class", value=special_reward["title"], inline=False)
        embed.add_field(name="🧬 Prestige", value=str(prestige), inline=True)
        embed.add_field(name="💰 Coins", value=str(coins), inline=True)
        embed.add_field(name="📦 Turn-ins", value=str(turnins), inline=True)
        embed.add_field(name="🔁 Builds", value=str(builds), inline=True)

        boost_lines = []
        for key, boost in BOOST_CATALOG.items():
            owned = boosts.get(key, False)
            label = boost["label"]
            status = "✅" if owned else "❌"
            cost = f"{boost['cost']} coins" if boost['cost'] > 0 else boost.get("note", "Special")
            boost_lines.append(f"{status} {label} — {cost}")
        embed.add_field(name="⚡ Boosts", value="\n".join(boost_lines), inline=False)

        view = RankView(uid, user, self.update_user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Rank(bot))
