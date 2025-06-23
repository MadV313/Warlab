# cogs/listregistered.py — Registered Player Overview with Reinforcements Added

import discord
from discord.ext import commands
from discord import app_commands
from collections import Counter

from utils.fileIO import load_file

USER_DATA = "data/user_profiles.json"
ENTRIES_PER_PAGE = 10

PRESTIGE_TITLES = {
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

DEFENCE_TYPES = ["Guard Dog", "Claymore Trap", "Barbed Fence", "Reinforced Gate", "Locked Container"]

class RegisteredListView(discord.ui.View):
    def __init__(self, pages, user):
        super().__init__(timeout=60)
        self.pages = pages
        self.current_page = 0
        self.user = user

        self.previous_button.disabled = True
        if len(pages) == 1:
            self.next_button.disabled = True

    async def update_embed(self, interaction):
        embed = discord.Embed(
            title="📋 Registered Player Overview",
            description=self.pages[self.current_page],
            color=0x2ecc71
        )
        embed.set_footer(text=f"Page {self.current_page + 1} of {len(self.pages)}")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⏪ Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("❌ Only you can navigate your menu.", ephemeral=True)

        self.current_page -= 1
        self.next_button.disabled = False
        self.previous_button.disabled = self.current_page == 0
        await self.update_embed(interaction)

    @discord.ui.button(label="Next ⏩", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("❌ Only you can navigate your menu.", ephemeral=True)

        self.current_page += 1
        self.previous_button.disabled = False
        self.next_button.disabled = self.current_page == len(self.pages) - 1
        await self.update_embed(interaction)

class ListRegistered(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="listregistered", description="Show all currently registered players and progress.")
    async def listregistered(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        profiles = await load_file(USER_DATA) or {}
        guild = interaction.guild
        user_ids = list(profiles.keys())
        entries = []

        for uid in user_ids:
            profile = profiles[uid]
            try:
                member = guild.get_member(int(uid)) or await guild.fetch_member(int(uid))
                name = member.display_name
            except:
                name = "[Unknown User]"

            prestige = profile.get("prestige", 0)
            prestige_pts = profile.get("prestige_points", 0)
            rank = profile.get("rank_level", 0)
            stash = Counter(profile.get("stash", []))
            reinforcements = profile.get("reinforcements", {})
            blueprints = profile.get("blueprints", [])
            scavenges = profile.get("scavenges_completed", 0)
            tasks = profile.get("tasks_completed", 0)
            raids = profile.get("raids_won", 0)
            turnins = profile.get("turnins_completed", 0)
            coins = profile.get("coins", 0)
            boosts = profile.get("boosts", [])
            boosts_owned = len(boosts)
            reinforce_total = sum(reinforcements.get(t, 0) for t in DEFENCE_TYPES)

            entries.append(
                f"• **{name}** (`{uid}`)\n"
                f"   - 🧬 Prestige: {prestige} ({prestige_pts}/200 pts)\n"
                f"   - 🔁 Builds: {len(blueprints)} | 📦 Turn-ins: {turnins} | 🪖 Raids: {raids}\n"
                f"   - 🔍 Scavenges: {scavenges} | 📝 Tasks: {tasks}\n"
                f"   - ⚡ Boosts: {boosts_owned}/3 | 💰 Coins: {coins} | 🛡️ Reinforcements: {reinforce_total}"
            )

        pages = [
            "\n\n".join(entries[i:i + ENTRIES_PER_PAGE])
            for i in range(0, len(entries), ENTRIES_PER_PAGE)
        ]

        embed = discord.Embed(
            title="📋 Registered Player Overview",
            description=pages[0] if pages else "No registered users found.",
            color=0x2ecc71
        )
        embed.set_footer(text=f"Page 1 of {len(pages)}")

        view = RegisteredListView(pages, interaction.user)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ListRegistered(bot))
