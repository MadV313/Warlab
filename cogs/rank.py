# cogs/rank.py

import discord
from discord.ext import commands
from discord import app_commands
import json, random
from datetime import datetime

USER_DATA_FILE      = "data/user_profiles.json"
WARLAB_CHANNEL_ID   = 1382187883590455296   # hard-coded broadcast channel

RANK_TITLES = {
    0: "Unranked Survivor",
    1: "Field Engineer",
    2: "Weapon Tech",
    3: "Shadow Engineer",
    4: "Warlab Veteran",
    5: "Legendary Craftsman"
}

SPECIAL_REWARDS = {
    1: {"title": "🔬 Scavenger Elite", "color": 0x3cb4fc},
    2: {"title": "💉 Weaponsmith Elite",    "color": 0x88e0a0},
    3: {"title": "☣️ Raider Elite",       "color": 0x880808}
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
    "perm_loot_boost" : {"label": "Permanent Loot Boost",    "cost": 1000},
    "coin_doubler"    : {"label": "Permanent Coin Doubler",  "cost": 1000},
}


class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close", style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.message.delete()


class RankView(discord.ui.View):
    def __init__(self, user_id: str, user_data: dict, update_callback):
        super().__init__(timeout=None)
        self.user_id         = user_id
        self.user_data       = user_data
        self.update_callback = update_callback

        self.prestige_button.disabled = self.user_data.get("builds_completed", 0) < 5
        self.add_item(CloseButton())

    @discord.ui.button(label="🧬 Prestige", style=discord.ButtonStyle.danger,
                       custom_id="prestige_button")
    async def prestige_button(self, itx: discord.Interaction, _):
        if str(itx.user.id) != self.user_id:
            await itx.response.send_message("❌ You can’t use another player’s UI.", ephemeral=True)
            return
        if self.user_data.get("builds_completed", 0) < 5:
            await itx.response.send_message("🔒 You need at least 5 full builds to prestige.",
                                            ephemeral=True)
            return

        rolled_id = random.choice(list(SPECIAL_REWARDS))
        self.user_data["special_class"]   = rolled_id
        self.user_data["prestige"]        = self.user_data.get("prestige", 0) + 1
        self.user_data["builds_completed"] = 0
        self.user_data["rank_level"]      = 0
        self.user_data["stash"]           = []
        self.user_data["boosts"]          = {}
        self.update_callback(self.user_id, self.user_data)

        reward = SPECIAL_REWARDS[rolled_id]
        await itx.response.send_message(
            f"🌟 Prestige successful! You rolled **{reward['title']}**.",
            ephemeral=True
        )

        ch = itx.client.get_channel(WARLAB_CHANNEL_ID)
        if ch:
            emb = discord.Embed(
                title="🧬 Prestige Unlocked!",
                description=(
                    f"{itx.user.mention} reached **Prestige {self.user_data['prestige']}**\n"
                    f"🎖 Prestige Class: **{reward['title']}**\n\n"
                    "🎲 Use `/rollblueprint` to try for a new schematic!"
                ),
                color=reward["color"], timestamp=datetime.utcnow()
            )
            emb.set_thumbnail(url=itx.user.display_avatar.url)
            await ch.send(embed=emb)

        guild  = itx.guild
        roleID = PRESTIGE_ROLES.get(self.user_data["prestige"])
        if guild and roleID:
            for r_id in PRESTIGE_ROLES.values():
                role = guild.get_role(r_id)
                if role and role in itx.user.roles and role.id != roleID:
                    await itx.user.remove_roles(role, reason="Old prestige role removed")
            new_role = guild.get_role(roleID)
            if new_role:
                await itx.user.add_roles(new_role, reason="Prestige reward role")

    @discord.ui.button(label="⚡ Buy Boost", style=discord.ButtonStyle.primary,
                       custom_id="buyboost_button")
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
            view=BoostDropdown(self.user_id, self.user_data,
                               self.update_callback, opts),
            ephemeral=True
        )


class BoostDropdown(discord.ui.View):
    def __init__(self, uid, udata, update_cb, options):
        super().__init__(timeout=60)
        self.uid       = uid
        self.udata     = udata
        self.update_cb = update_cb
        self.select    = discord.ui.Select(placeholder="Select a boost…",
                                           options=options,
                                           custom_id="boost_select")
        self.select.callback = self.process
        self.add_item(self.select)

    async def process(self, itx: discord.Interaction):
        if str(itx.user.id) != self.uid:
            await itx.response.send_message("❌ This dropdown isn’t yours.", ephemeral=True)
            return

        key   = self.select.values[0]
        meta  = BOOST_CATALOG[key]
        cost  = meta["cost"]
        coins = self.udata.get("coins", 0)

        if coins < cost:
            await itx.response.send_message(f"❌ You need {cost} coins for that boost.",
                                            ephemeral=True)
            return

        self.udata["coins"] -= cost
        self.udata.setdefault("boosts", {})[key] = True
        self.update_cb(self.uid, self.udata)

        await itx.response.send_message(f"✅ Boost purchased: **{meta['label']}**",
                                        ephemeral=True)


class Rank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _load(self):
        try:
            with open(USER_DATA_FILE) as f:
                return json.load(f)
        except:
            return {}

    def _save(self, data):
        with open(USER_DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _update_user(self, uid, data):
        all_d        = self._load()
        all_d[uid]   = data
        self._save(all_d)

    def _determine_special_reward(self, ud: dict):
        if ud.get("blueprints_complete"):
            return SPECIAL_REWARDS[1]
        if ud.get("scavenges", 0) >= 100:
            return SPECIAL_REWARDS[2]
        if ud.get("successful_raids", 0) >= 25:
            return SPECIAL_REWARDS[3]
        return None

    @app_commands.command(name="rank", description="View rank, prestige & buy boosts.")
    async def rank(self, itx: discord.Interaction):
        uid      = str(itx.user.id)
        profiles = self._load()
        user     = profiles.get(uid)

        if not user:
            await itx.response.send_message("❌ You don’t have a profile yet. Please use `/register` first.",
                                            ephemeral=True)
            return

        prestige  = user.get("prestige", 0)
        level     = user.get("rank_level", 0)
        coins     = user.get("coins", 0)
        builds    = user.get("builds_completed", 0)
        turnins   = user.get("turnins_completed", 0)
        boosts    = user.get("boosts", {})
        class_id  = user.get("special_class")

        reward = self._determine_special_reward(user) \
                 or SPECIAL_REWARDS.get(class_id)
        color  = reward["color"] if reward else 0x88e0ef

        emb = discord.Embed(title=f"🏅 {itx.user.display_name}'s Rank",
                            color=color)
        rank_title = RANK_TITLES.get(prestige, "Unknown Survivor")
        emb.add_field(name="🎖️ Rank Title", value=rank_title, inline=False)
        if reward:
            emb.add_field(name="🧬 Prestige Class", value=reward["title"],
                          inline=False)
        emb.add_field(name="🧬 Prestige", value=str(prestige))
        emb.add_field(name="💰 Coins",    value=str(coins))
        emb.add_field(name="📦 Turn-ins", value=str(turnins))
        emb.add_field(name="🔁 Builds",   value=str(builds))

        lines = []
        for k, meta in BOOST_CATALOG.items():
            owned  = boosts.get(k, False)
            status = "✅" if owned else "❌"
            lines.append(f"{status} {meta['label']} — {meta['cost']} coins")
        emb.add_field(name="⚡ Boosts", value="\n".join(lines), inline=False)

        await itx.response.send_message(
            embed=emb,
            view=RankView(uid, user, self._update_user),
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Rank(bot))
