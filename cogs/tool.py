# cogs/tool.py — Admin: Give or remove tools (flat list stash logic to match scavenge/task)

import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
TOOLS = ["Saw", "Nails", "Pliers", "Hammer"]

class ToolManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
        try:
            await interaction.response.defer(ephemeral=True)
            print(f"📥 /tool: {interaction.user.display_name} {action} {quantity}×{item} → {user.display_name}")

            if quantity <= 0:
                await interaction.followup.send("⚠️ Quantity must be greater than **0**.", ephemeral=True)
                return

            profiles = await load_file(USER_DATA) or {}
            uid = str(user.id)
            profile = profiles.get(uid, {})
            stash = profile.get("stash", [])

            # Handle legacy formats
            if not isinstance(stash, list):
                stash = []

            # ── GIVE ───────────────────────
            if action == "give":
                stash.extend([item] * quantity)
                msg = f"✅ Gave **{quantity} × {item}** to {user.mention}."

            # ── REMOVE ─────────────────────
            else:
                removed = 0
                new_stash = []
                for s in stash:
                    if s == item and removed < quantity:
                        removed += 1
                        continue
                    new_stash.append(s)

                stash = new_stash
                msg = (
                    f"🗑 Removed **{removed} × {item}** from {user.mention}."
                    if removed else
                    f"⚠️ {user.mention} doesn't have that many **{item}**."
                )

            profile["stash"] = stash
            profiles[uid] = profile
            await save_file(USER_DATA, profiles)
            await interaction.followup.send(msg, ephemeral=True)

        except Exception as e:
            print(f"❌ Error in /tool command: {type(e).__name__}: {e}")
            try:
                await interaction.followup.send(f"❌ Unexpected error: {e}", ephemeral=True)
            except:
                pass

async def setup(bot):
    await bot.add_cog(ToolManager(bot))
