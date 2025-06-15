# cogs/rank.py

import discord
from discord.ext import commands
from discord import app_commands
import json
from datetime import datetime

USER_DATA_FILE = "data/user_profiles.json"
WARLAB_CHANNEL_ID = 1382187883590455296  # 🔒 Hardcoded Warlab channel

RANK_TITLES = {
    0: "Unranked Survivor",
    1: "Tier 1 Builder",
    2: "Field Engineer",
    3: "Weapon Tech",
    4: "Raider Elite",
    5: "Master Craftsman",
    6: "Architect Prime",
    7: "Shadow Engineer",
    8: "Warlab Veteran",
    9: "Legendary Craftsman"
}

SPECIAL_REWARDS = {
    1: {"title": "💉 Technician", "color": 0x3cb4fc},
    2: {"title": "🔬 Scavenger Elite", "color": 0x88e0a0},
    3: {"title": "☣️ Black Lab Agent", "color": 0x880808}
}

# Prestige role mapping (fill with real role IDs from your server)
PRESTIGE_ROLES = {
    1: 1200000000000000001,
    2: 1200000000000000002,
    3: 1200000000000000003,
    4: 1200000000000000004,
    5: 1200000000000000005
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

        self.user_data["prestige"] = self.user_data.get("prestige", 0) + 1
        self.user_data["builds_completed"] = 0
        self.user_data["rank_level"] = 0
        self.user_data["stash"] = []
        self.user_data["boosts"] = {}
        self.update_callback(self.user_id, self.user_data)

        await interaction.response.send_message("🌟 Prestige successful! Your stash and rank were reset. Cosmetic perks unlocked.", ephemeral=True)

        # 🔔 Prestige Shoutout
        prestige_level = self.user_data["prestige"]
        reward_text = f"Unlocked prestige level: **{prestige_level}**"
        if prestige_level == 4:
            reward_text += " — Lab Skins unlocked!"
        elif prestige_level == 5:
            reward_text += " — Warlab Blacksite + Elite perks unlocked!"

        warlab_channel = interaction.client.get_channel(WARLAB_CHANNEL_ID)
        if warlab_channel:
            embed = discord.Embed(
                title=f"🧬 Prestige Unlocked!",
                description=(
                    f"{interaction.user.mention} has reached **Prestige Level {prestige_level}**!\n"
                    f"{reward_text}\n\n🎲 Use `/rollblueprint` to try for a new schematic!"
                ),
                color=0x9b59b6,
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text="Warlab Protocol: Prestige Activated")

            await warlab_channel.send(embed=embed)

        # 🎖 Auto-role assignment (if mapped)
        guild = interaction.guild
        role_id = PRESTIGE_ROLES.get(prestige_level)
        if guild and role_id:
            # Remove all previous prestige roles
            roles_to_remove = [guild.get_role(rid) for lvl, rid in PRESTIGE_ROLES.items() if lvl != prestige_level]
            for r in roles_to_remove:
                if r and r in interaction.user.roles:
                    await interaction.user.remove_roles(r, reason="Old prestige role removed")
        
            # Add new prestige role
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

        embed_color = 0x88e0ef
        special_title = None

        if prestige >= 10:
            special_title = SPECIAL_REWARDS[3]
        elif prestige >= 5:
            special_title = SPECIAL_REWARDS[2]
        elif prestige >= 2:
            special_title = SPECIAL_REWARDS[1]

        if special_title:
            embed_color = special_title["color"]

        embed = discord.Embed(title=f"🏅 {interaction.user.display_name}'s Rank", color=embed_color)
        embed.add_field(name="🎖️ Rank Title", value=RANK_TITLES.get(level, "???"), inline=False)
        if special_title:
            embed.add_field(name="🧬 Prestige Class", value=special_title["title"], inline=False)
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
