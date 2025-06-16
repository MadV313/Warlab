# cogs/tool.py — Admin: Give or remove tools from a player (Dropdown Flow)

import discord
from typing import Literal
from discord.ext import commands
from discord import app_commands
from utils.fileIO import load_file, save_file

USER_DATA   = "data/user_profiles.json"
TOOLS_FILE  = "data/blackmarket_items_master.json"


class ToolDropdown(discord.ui.Select):
    def __init__(self, target: discord.Member, action: str, quantity: int, tool_list: list[str]):
        options = [discord.SelectOption(label=t, value=t) for t in tool_list]
        super().__init__(placeholder="Select a tool", options=options, min_values=1, max_values=1)
        self.target   = target
        self.action   = action  # "give" | "remove"
        self.quantity = quantity

    async def callback(self, interaction: discord.Interaction):
        selected_tool = self.values[0]

        profiles = await load_file(USER_DATA) or {}
        uid      = str(self.target.id)
        profile  = profiles.get(uid, {"inventory": []})

        # ── Give ────────────────────────────────────────────────
        if self.action == "give":
            for _ in range(self.quantity):
                profile["inventory"].append({"item": selected_tool, "rarity": "Admin"})
            await interaction.response.send_message(
                f"✅ Gave **{self.quantity}× {selected_tool}** to {self.target.mention}.",
                ephemeral=True
            )

        # ── Remove ──────────────────────────────────────────────
        else:  # remove
            removed = 0
            new_inv = []
            for entry in profile["inventory"]:
                if entry.get("item") == selected_tool and removed < self.quantity:
                    removed += 1
                    continue
                new_inv.append(entry)

            profile["inventory"] = new_inv
            if removed > 0:
                await interaction.response.send_message(
                    f"🗑 Removed **{removed}× {selected_tool}** from {self.target.mention}.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"⚠️ {self.target.mention} does not have that tool or not enough to remove.",
                    ephemeral=True
                )

        profiles[uid] = profile
        await save_file(USER_DATA, profiles)


class ToolSelectView(discord.ui.View):
    def __init__(self, target: discord.Member, action: str, quantity: int, tool_list: list[str]):
        super().__init__(timeout=60)
        self.add_item(ToolDropdown(target, action, quantity, tool_list))


class ToolManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="tool",
        description="Admin: Give or remove tools from a player."
    )
    @app_commands.describe(
        action="Choose to give or remove a tool",
        user="Target player",
        quantity="How many to give or remove"
    )
    async def tool(
        self,
        interaction: discord.Interaction,
        action: Literal["give", "remove"],
        user: discord.Member,
        quantity: int
    ):
        if quantity <= 0:
            await interaction.response.send_message("⚠️ Quantity must be greater than 0.", ephemeral=True)
            return

        items_db  = await load_file(TOOLS_FILE) or {}
        tool_list = [name for name, meta in items_db.items() if meta.get("type") == "tool"]

        if not tool_list:
            await interaction.response.send_message("❌ No tools found in the database.", ephemeral=True)
            return

        view = ToolSelectView(user, action.lower(), quantity, sorted(tool_list))
        await interaction.response.send_message(
            f"🧰 Select a tool to **{action.lower()}** for {user.mention}:",
            view=view,
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(ToolManager(bot))
