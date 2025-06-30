import discord
from discord.ext import commands
from discord import app_commands
from utils.storageClient import load_file

USER_DATA_FILE = "data/user_profiles.json"

class CloseButton(discord.ui.Button):
    def __init__(self, ephemeral: bool):
        super().__init__(label="Close", style=discord.ButtonStyle.danger)
        self.ephemeral = ephemeral

    async def callback(self, interaction: discord.Interaction):
        try:
            if self.ephemeral:
                await interaction.response.edit_message(content="❌ Leaderboard view closed.", embed=None, view=None)
            else:
                await interaction.message.delete()
        except Exception as e:
            print(f"❌ Failed to close leaderboard view: {e}")

class LeaderboardView(discord.ui.View):
    def __init__(self, ephemeral: bool):
        super().__init__(timeout=300)
        self.add_item(CloseButton(ephemeral))

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="Top 3: raids won, builds completed, coins held.")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        profiles = await load_file(USER_DATA_FILE) or {}
        if not profiles:
            await interaction.followup.send("❌ Failed to load player data.", ephemeral=True)
            return

        raids = []
        builds = []
        coins = []

        for uid, profile in profiles.items():
            name = profile.get("name", f"<@{uid}>")  # fallback to mention
            raids.append((name, profile.get("successful_raids", 0)))
            builds.append((name, profile.get("builds_completed", 0)))
            coins.append((name, profile.get("coins", 0)))

        raids.sort(key=lambda x: x[1], reverse=True)
        builds.sort(key=lambda x: x[1], reverse=True)
        coins.sort(key=lambda x: x[1], reverse=True)

        def format_top(title, data, emoji):
            if not data or all(v[1] == 0 for v in data):
                return f"{emoji} No data available."
            return f"**{emoji} {title}**\n" + "\n".join(
                f"`#{i+1}` {name} — **{value}**" for i, (name, value) in enumerate(data[:3])
            )

        embed = discord.Embed(
            title="🏆 WARLAB Leaderboards",
            color=0xFFD700
        )
        embed.add_field(name="🪖 Top Raiders", value=format_top("Raids Won", raids, "🪖"), inline=False)
        embed.add_field(name="🛠️ Top Builders", value=format_top("Builds Completed", builds, "🛠️"), inline=False)
        embed.add_field(name="🪙 Top Coin Holders", value=format_top("Coins", coins, "🪙"), inline=False)
        embed.set_footer(text="Based on global user data")

        view = LeaderboardView(ephemeral=True)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
