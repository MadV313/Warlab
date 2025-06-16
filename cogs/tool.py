# cogs/tool.py — Admin: Give or remove tools from a player (Blueprint-Style Format)

import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"

# ✅ Hardcoded tool list
HARDCODED_TOOLS = [
    "Saw",
    "Nails",
    "Pliers",
    "Hammer"
]

class ToolManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="tool",
        description="Admin: Give or remove tools from a player."
    )
    @app_commands.describe(
        action="Give or remove tool",
        user="Target player",
        item="Tool name (Saw, Nails, etc)",
        quantity="How many to give or remove"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def tool(
        self,
        interaction: discord.Interaction,
        action: Literal["give", "remove"],
        user: discord.Member,
        item: str,
        quantity: int
    ):
        if quantity <= 0 and action == "give":
            await interaction.response.send_message("⚠️ Quantity must be greater than 0.", ephemeral=True)
            return

        item = item.strip()
        if item not in HARDCODED_TOOLS:
            await interaction.response.send_message(
                f"❌ Invalid tool.\nChoose from: {', '.join(HARDCODED_TOOLS)}",
                ephemeral=True
            )
            return

        profiles = await load_file(USER_DATA) or {}
        uid = str(user.id)
        profile = profiles.get(uid, {"inventory": []})

        # ── Give ────────────────────────────────────────────────
        if action == "give":
            for _ in range(quantity):
                profile["inventory"].append({"item": item, "rarity": "Admin"})
            await interaction.response.send_message(
                f"✅ Gave **{quantity}× {item}** to {user.mention}.",
                ephemeral=True
            )

        # ── Remove ──────────────────────────────────────────────
        elif action == "remove":
            removed = 0
            new_inv = []
            for entry in profile["inventory"]:
                if entry.get("item") == item and removed < quantity:
                    removed += 1
                    continue
                new_inv.append(entry)

            profile["inventory"] = new_inv
            if removed > 0:
                await interaction.response.send_message(
                    f"🗑 Removed **{removed}× {item}** from {user.mention}.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"⚠️ {user.mention} does not have that tool or not enough to remove.",
                    ephemeral=True
                )

        profiles[uid] = profile
        await save_file(USER_DATA, profiles)

    @tool.autocomplete("item")
    async def autocomplete_tool(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=t, value=t)
            for t in HARDCODED_TOOLS if current.lower() in t.lower()
        ][:25]

async def setup(bot):
    await bot.add_cog(ToolManager(bot))
