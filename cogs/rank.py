# cogs/rank.py — Fixed Prestige Display + Proper Prestige Class Logic (Remote Persistence + Debug Prints)

import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime
import pytz

from utils.storageClient import load_file, save_file

USER_DATA_FILE = "data/user_profiles.json"
WARLAB_CHANNEL_ID = 1382187883590455296

RANK_TITLES = {
    0: "Unranked Survivor",
    1: "Field Engineer",
    2: "Weapon Tech",
    3: "Shadow Engineer",
    4: "Warlab Veteran",
    5: "Legendary Craftsman",
    6: "Legend",
    7: "Apex",
    8: "Ghost",
    9: "Mythic",
    10: "Master Chief"
}

SPECIAL_REWARDS = {
    1: {"title": "☣️ Raider Elite", "color": 0x880808},
    2: {"title": "💉 Weaponsmith Elite", "color": 0x88e0a0},
    3: {"title": "🔬 Scavenger Elite", "color": 0x3cb4fc}
}

PRESTIGE_ROLES = {
    1: 1184964035863650395,
    2: 1184963951746879638,
    3: 1184964276776091741,
    4: 1184964646055190558,
    5: 1184964764313583657
}

BOOST_CATALOG = {
    "daily_loot_boost": {"label": "Daily Loot Boost (24 h)", "cost": 100},
    "perm_loot_boost": {"label": "Permanent Loot Boost", "cost": 5000},
    "coin_doubler": {"label": "Permanent Coin Doubler", "cost": 5000}
}

def is_weekend():
    return datetime.now(pytz.utc).weekday() in [4, 5, 6]

class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close", style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.message.edit(content="❌ Rank view closed", embed=None, view=None)

class RankView(discord.ui.View):
    def __init__(self, user_id: str, user_data: dict, update_callback):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.user_data = user_data
        self.update_callback = update_callback
        self.add_item(CloseButton())

    @discord.ui.button(label="🧬 Prestige", style=discord.ButtonStyle.danger, custom_id="prestige_button")
    async def prestige_button(self, itx: discord.Interaction, _):
        if str(itx.user.id) != self.user_id:
            await itx.response.send_message("❌ You can’t use another player’s UI.", ephemeral=True)
            return

        points = self.user_data.get("prestige_points", 0)
        if points < 200:
            await itx.response.send_message("🔒 You need **200 prestige points** to prestige.\nEarn 50 per build or successful raid.", ephemeral=True)
            return

        print(f"🧬 [Prestige] {self.user_id} prestiging with {points} points.")

        skin = self.user_data.get("active_skin", "")
        raids = self.user_data.get("successful_raids", 0)
        stash = self.user_data.get("stash", [])
        scavenges = self.user_data.get("scavenges", 0)

        reward = None
        if skin == "Dark Ops" and raids >= 25:
            reward = SPECIAL_REWARDS[1]
            self.user_data["special_class"] = 1
        elif skin == "Architect's Vault" and len([b for b in stash if "Blueprint" in b]) >= 12:
            reward = SPECIAL_REWARDS[2]
            self.user_data["special_class"] = 2
        elif skin == "Scavenger's Haven" and scavenges >= 100:
            reward = SPECIAL_REWARDS[3]
            self.user_data["special_class"] = 3
        else:
            self.user_data["special_class"] = None

        self.user_data["prestige"] = self.user_data.get("prestige", 0) + 1
        self.user_data["prestige_points"] -= 200
        self.user_data["builds_completed"] = 0
        self.user_data["rank_level"] = 0
        self.user_data["stash"] = []
        self.user_data["boosts"] = {}

        print(f"✅ [Prestige] Updated user: {self.user_data}")
        await self.update_callback(self.user_id, self.user_data)

        title = reward['title'] if reward else "No Prestige Class — equip a qualifying Lab Skin and meet requirements to unlock one."
        color = reward["color"] if reward else 0x5865f2

        await itx.response.send_message(f"🌟 Prestige successful!\n🎖 **{title}**", ephemeral=True)

        ch = itx.client.get_channel(WARLAB_CHANNEL_ID)
        if ch:
            emb = discord.Embed(
                title="🧬 Prestige Unlocked!",
                description=(f"{itx.user.mention} reached **Prestige {self.user_data['prestige']}**\n"
                             f"🎖 Prestige Class: **{title}**\n\n"
                             "🎲 Use `/rollblueprint` to try for a new schematic!"),
                color=color, timestamp=datetime.utcnow()
            )
            emb.set_thumbnail(url=itx.user.display_avatar.url)
            await ch.send(embed=emb)

        guild = itx.guild
        roleID = PRESTIGE_ROLES.get(self.user_data["prestige"])
        if guild and roleID:
            for r_id in PRESTIGE_ROLES.values():
                role = guild.get_role(r_id)
                if role and role in itx.user.roles and role.id != roleID:
                    await itx.user.remove_roles(role)
            new_role = guild.get_role(roleID)
            if new_role:
                await itx.user.add_roles(new_role)

    @discord.ui.button(label="⚡ Buy Boost", style=discord.ButtonStyle.primary, custom_id="buyboost_button")
    async def buy_boost_button(self, itx: discord.Interaction, _):
        if str(itx.user.id) != self.user_id:
            await itx.response.send_message("❌ You can’t use another player’s UI.", ephemeral=True)
            return

        owned = self.user_data.get("boosts", {})
        coins = self.user_data.get("coins", 0)

        opts = []
        for key, meta in BOOST_CATALOG.items():
            if owned.get(key):
                continue
            label = f"{meta['label']} — {meta['cost']} coins"
            opts.append(discord.SelectOption(label=label, value=key))

        if not opts:
            await itx.response.send_message("✅ You already own every boost.", ephemeral=True)
            return

        await itx.response.send_message(
            "Choose a boost to purchase:",
            view=BoostDropdown(self.user_id, self.user_data, self.update_callback, opts),
            ephemeral=True
        )

class BoostDropdown(discord.ui.View):
    def __init__(self, uid, udata, update_cb, options):
        super().__init__(timeout=300)
        self.uid = uid
        self.udata = udata
        self.update_cb = update_cb
        self.select = discord.ui.Select(placeholder="Select a boost…", options=options, custom_id="boost_select")
        self.select.callback = self.process
        self.add_item(self.select)

    async def process(self, itx: discord.Interaction):
        if str(itx.user.id) != self.uid:
            await itx.response.send_message("❌ This dropdown isn’t yours.", ephemeral=True)
            return

        key = self.select.values[0]
        meta = BOOST_CATALOG[key]
        cost = meta["cost"]
        coins = self.udata.get("coins", 0)

        if coins < cost:
            await itx.response.send_message(f"❌ You need {cost} coins for that boost.", ephemeral=True)
            return

        self.udata["coins"] -= cost
        self.udata.setdefault("boosts", {})[key] = True
        print(f"⚡ [Boost] {self.uid} bought {key} for {cost} coins.")
        await self.update_cb(self.uid, self.udata)

        await itx.response.send_message(f"✅ Boost purchased: **{meta['label']}**", ephemeral=True)

class Rank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _update_user(self, uid, data):
        print(f"💾 [Rank] Saving profile for UID {uid}")
        all_profiles = await load_file(USER_DATA_FILE) or {}
        all_profiles[uid] = data
        await save_file(USER_DATA_FILE, all_profiles)

    @app_commands.command(name="rank", description="View rank, prestige & buy boosts.")
    async def rank(self, itx: discord.Interaction):
        uid = str(itx.user.id)
        profiles = await load_file(USER_DATA_FILE) or {}
        user = profiles.get(uid)

        if not user:
            await itx.response.send_message("❌ You don’t have a profile yet. Please use `/register` first.", ephemeral=True)
            return

        from utils.prestigeUtils import get_prestige_progress
        progress = get_prestige_progress(user.get("prestige_points", 0))
        prestige = progress["current_rank"]
        points = progress["points"]
        threshold = progress["next_threshold"]

        user["prestige"] = prestige
        await self._update_user(uid, user)

        class_id = user.get("special_class")
        reward = SPECIAL_REWARDS.get(class_id)
        color = reward["color"] if reward else 0x88e0ef

        emb = discord.Embed(title=f"🏅 {itx.user.display_name}'s Rank", color=color)
        emb.add_field(name="🎖️ Rank Title", value=RANK_TITLES.get(prestige, "Unknown Survivor"), inline=False)
        if threshold:
            emb.add_field(name="🧬 Prestige", value=f"Tier {prestige} — {points}/{threshold}", inline=False)
        else:
            emb.add_field(name="🧬 Prestige", value=f"Tier {prestige} — MAX", inline=False)

        emb.add_field(name="💰 Coins", value=str(user.get("coins", 0)))
        emb.add_field(name="📦 Turn-ins", value=str(user.get("turnins_completed", 0)))
        emb.add_field(name="🔁 Builds Completed", value=str(user.get("builds_completed", 0)))
        emb.add_field(name="🪖 Raids Won", value=str(user.get("successful_raids", 0)))
        emb.add_field(name="🔍 Scavenges", value=str(user.get("scavenges", 0)))
        emb.add_field(name="📝 Tasks Done", value=str(user.get("tasks_completed", 0)))

        boosts = user.get("boosts", {})
        lines = []
        for k, meta in BOOST_CATALOG.items():
            status = "✅" if boosts.get(k) else "❌"
            lines.append(f"{status} {meta['label']} — {meta['cost']} coins")
        emb.add_field(name="⚡ Boosts", value="\n".join(lines), inline=False)

        await itx.response.send_message(embed=emb, view=RankView(uid, user, self._update_user), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Rank(bot))
