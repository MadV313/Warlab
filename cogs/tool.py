# cogs/tool.py — Admin: Give or remove tools from a player (hard-coded dropdown list)

import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"

# Hard-coded tool catalogue (keeps the command fast & avoids DB look-ups)
TOOLS = ["Saw", "Nails", "Pliers", "Hammer"]

class ToolManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ─────────────────────────────────────────────────────────────
    @app_commands.command(
        name="tool",
        description="Admin-only: Give or remove tools from a player."
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        action="Give or remove tool(s)",
        user="Target player",
        item="Tool to give/remove",
        quantity="How many to give or remove (≥1)"
    )
    async def tool(
        self,
        interaction: discord.Interaction,
        action: Literal["give", "remove"],
        user: discord.Member,
        item: Literal["Saw", "Nails", "Pliers", "Hammer"],
        quantity: int
    ):
        print(f"📥 /tool command triggered by {interaction.user.display_name} — {action} {quantity} × {item} to {user.display_name}")
        await interaction.response.defer(ephemeral=True)

        if quantity <= 0:
            await interaction.followup.send("⚠️ Quantity must be greater than **0**.", ephemeral=True)
            return

        profiles = await load_file(USER_DATA) or {}
        uid = str(user.id)
        profile = profiles.get(uid, {"inventory": []})

        # ── GIVE ───────────────────────────────────────────────
        if action == "give":
            for _ in range(quantity):
                profile["inventory"].append({"item": item, "rarity": "Admin"})
            await interaction.followup.send(
                f"✅ Gave **{quantity} × {item}** to {user.mention}.",
                ephemeral=True
            )

        # ── REMOVE ─────────────────────────────────────────────
        else:  # action == "remove"
            removed, new_inv = 0, []
            for entry in profile["inventory"]:
                if entry.get("item") == item and removed < quantity:
                    removed += 1
                    continue
                new_inv.append(entry)

            profile["inventory"] = new_inv
            msg = (
                f"🗑 Removed **{removed} × {item}** from {user.mention}."
                if removed
                else f"⚠️ {user.mention} doesn’t have that many **{item}**."
            )
            await interaction.followup.send(msg, ephemeral=True)

        # ── persist changes ────────────────────────────────────
        profiles[uid] = profile
        await save_file(USER_DATA, profiles)

async def setup(bot):
    await bot.add_cog(ToolManager(bot))
