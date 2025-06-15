# cogs/tool.py — Admin: Give or remove tools from a player (Dropdown Flow)

import discord
from typing import Literal
from discord.ext import commands
from discord import app_commands
from utils.fileIO import load_file, save_file

USER_DATA   = "data/user_profiles.json"
TOOLS_FILE  = "data/blackmarket_items_master.json"


# ──────────────────────────────────────────────────────────────────
class ToolDropdown(discord.ui.Select):
    def __init__(self, target: discord.Member, action: str, tool_list: list[str]):
        options = [discord.SelectOption(label=t, value=t) for t in tool_list]
        super().__init__(placeholder="Select a tool", options=options, min_values=1, max_values=1)
        self.target  = target
        self.action  = action   # "give" | "remove"

    async def callback(self, interaction: discord.Interaction):
        selected_tool = self.values[0]

        profiles = await load_file(USER_DATA) or {}
        uid      = str(self.target.id)
        profile  = profiles.get(uid, {"inventory": []})

        # ── Give ────────────────────────────────────────────────
        if self.action == "give":
            profile["inventory"].append({"item": selected_tool, "rarity": "Admin"})
            await interaction.response.send_message(
                f"✅ Gave **1× {selected_tool}** to {self.target.mention}.",
                ephemeral=True
            )

        # ── Remove ──────────────────────────────────────────────
        else:  # remove
            removed = False
            new_inv = []
            for entry in profile["inventory"]:
                if entry.get("item") == selected_tool and not removed:
                    removed = True
                    continue
                new_inv.append(entry)

            profile["inventory"] = new_inv
            if removed:
                await interaction.response.send_message(
                    f"🗑 Removed **1× {selected_tool}** from {self.target.mention}.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"⚠️ {self.target.mention} does not have that tool.",
                    ephemeral=True
                )

        profiles[uid] = profile
        await save_file(USER_DATA, profiles)


class ToolSelectView(discord.ui.View):
    def __init__(self, target: discord.Member, action: str, tool_list: list[str]):
        super().__init__(timeout=60)
        self.add_item(ToolDropdown(target, action, tool_list))


# ──────────────────────────────────────────────────────────────────
class ToolManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="tool",
        description="Admin: Give or remove tools from a player."
    )
    @app_commands.describe(
        user="Target player",
        action="Choose to give or remove a tool"
    )
    async def tool(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        action: Literal["give", "remove"]
    ):
        # Permissions check ---------------------------------------------------
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You don’t have permission to use this.",
                ephemeral=True
            )
            return

        # Fetch valid tools ----------------------------------------------------
        items_db  = await load_file(TOOLS_FILE) or {}
        tool_list = [name for name, meta in items_db.items() if meta.get("type") == "tool"]

        if not tool_list:
            await interaction.response.send_message(
                "❌ No tools found in the database.",
                ephemeral=True
            )
            return

        # Open dropdown UI -----------------------------------------------------
        view = ToolSelectView(user, action.lower(), sorted(tool_list))
        await interaction.response.send_message(
            f"🧰 Select a tool to **{action.lower()}** for {user.mention}:",
            view=view,
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(ToolManager(bot))
