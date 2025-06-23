# cogs/listregistered.py — Paginated list of registered players with progress overview

import discord
from discord.ext import commands
from discord import app_commands
from collections import Counter

from utils.fileIO import load_file

USER_DATA = "data/user_profiles.json"
ENTRIES_PER_PAGE = 10

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

            stash = Counter(profile.get("stash", []))
            reinforcements = profile.get("reinforcements", {})
            blueprints = profile.get("blueprints", [])
            prestige = profile.get("prestige", 0)

            entries.append(
                f"• **{name}** (`{uid}`)\n"
                f"   - 🎒 Stash: {sum(stash.values())} items\n"
                f"   - 🛡️ Defenses: {sum(reinforcements.values())} active\n"
                f"   - 🧰 Builds: {len(blueprints)} completed\n"
                f"   - 🏅 Rank: Prestige {prestige}\n"
            )

        # Paginate every 10 entries
        pages = [
            "\n".join(entries[i:i + ENTRIES_PER_PAGE])
            for i in range(0, len(entries), ENTRIES_PER_PAGE)
        ]

        embed = discord.Embed(
            title="📋 Registered Player Overview",
            description=pages[0],
            color=0x2ecc71
        )
        embed.set_footer(text=f"Page 1 of {len(pages)}")

        view = RegisteredListView(pages, interaction.user)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ListRegistered(bot))
