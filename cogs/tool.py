# cogs/tool.py — Admin: Give or remove tools from a player (Dropdown Flow)

import discord
from typing import Literal
from discord.ext import commands
from discord import app_commands
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
TOOLS_FILE = "data/blackmarket_items_master.json"

class ToolDropdown(discord.ui.Select):
    def __init__(self, user: discord.Member, action: str, tool_list):
        options = [
            discord.SelectOption(label=tool, value=tool) for tool in tool_list
        ]
        super().__init__(placeholder="Select a tool", options=options, min_values=1, max_values=1)
        self.user = user
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        selected_tool = self.values[0]

        profiles = await load_file(USER_DATA) or {}
        user_id = str(self.user.id)
        profile = profiles.get(user_id, {"inventory": []})

        if self.action == "give":
            profile["inventory"].append({"item": selected_tool, "rarity": "Admin"})
            await interaction.response.send_message(f"✅ Gave **1x {selected_tool}** to {self.user.mention}.", ephemeral=True)

        elif self.action == "remove":
            removed = False
            new_inventory = []
            for entry in profile["inventory"]:
                if entry.get("item") == selected_tool and not removed:
                    removed = True
                    continue
                new_inventory.append(entry)
            profile["inventory"] = new_inventory
            if removed:
                await interaction.response.send_message(f"🗑 Removed **1x {selected_tool}** from {self.user.mention}.", ephemeral=True)
            else:
                await interaction.response.send_message(f"⚠️ {self.user.mention} does not have that tool.", ephemeral=True)
            return

        profiles[user_id] = profile
        await save_file(USER_DATA, profiles)


class ToolSelectView(discord.ui.View):
    def __init__(self, user, action, tool_list):
        super().__init__()
        self.add_item(ToolDropdown(user, action, tool_list))


class ToolManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tool", description="Admin: Give or remove tools from a player")
    @app_commands.describe(
        user="Target player",
        action="Give or remove tools (1 at a time)"
    )
    async def tool(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        action: app_commands.Transform[str, app_commands.Choice[Literal["give", "remove"]]]
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You don’t have permission to use this.", ephemeral=True)
            return

        action = action.lower()

        # Load valid tools
        all_items = await load_file(TOOLS_FILE) or {}
        tool_list = [name for name, data in all_items.items() if data.get("type") == "tool"]

        if not tool_list:
            await interaction.response.send_message("❌ No tools found in the database.", ephemeral=True)
            return

        view = ToolSelectView(user, action, sorted(tool_list))
        await interaction.response.send_message(f"🧰 Select a tool to **{action}** for {user.mention}:", view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ToolManager(bot))
