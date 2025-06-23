import discord
from discord.ext import commands
from discord import app_commands
from utils.storageClient import load_file

USER_DATA = "data/user_profiles.json"

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="View the top 3 players for raids, builds, and coins.")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)

        data = await load_file(USER_DATA) or {}

        # Build sortable lists
        raid_wins = []
        builds_done = []
        coins = []

        for uid, profile in data.items():
            name = profile.get("name", "Unknown")
            raid_wins.append((name, profile.get("raidWins", 0)))
            builds_done.append((name, profile.get("buildsComplete", 0)))
            coins.append((name, profile.get("coins", 0)))

        raid_wins.sort(key=lambda x: x[1], reverse=True)
        builds_done.sort(key=lambda x: x[1], reverse=True)
        coins.sort(key=lambda x: x[1], reverse=True)

        def fmt_rankings(title, items, emoji):
            result = [f"**{emoji} {title}**"]
            for i, (name, val) in enumerate(items[:3], 1):
                result.append(f"`#{i}` {name} — **{val}**")
            return "\n".join(result) if len(result) > 1 else f"{emoji} No data available."

        embed = discord.Embed(
            title="🏆 WARLAB Leaderboards",
            color=0xffd700
        )
        embed.add_field(name="🪖 Raid Wins", value=fmt_rankings("Top Raid Wins", raid_wins, "🪖"), inline=False)
        embed.add_field(name="🛠️ Builds Completed", value=fmt_rankings("Top Builders", builds_done, "🛠️"), inline=False)
        embed.add_field(name="🪙 Coins", value=fmt_rankings("Top Richest", coins, "🪙"), inline=False)
        embed.set_footer(text="WARLAB | SV13 Bot")

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
