# cogs/part.py — Admin: Give or remove parts from a player (flat stash format)

import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
GUN_PARTS = "data/item_recipes.json"
ARMOR_PARTS = "data/armor_blueprints.json"

class PartManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_all_parts(self):
        guns = await load_file(GUN_PARTS) or {}
        armors = await load_file(ARMOR_PARTS) or {}
        parts = set()

        for data in list(guns.values()) + list(armors.values()):
            for p in data.get("required_parts", []):
                parts.add(p)

        return sorted(parts)

    @app_commands.command(name="part", description="Admin: Give or remove parts from a player.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        action="Give or remove a part",
        user="Target player",
        item="Name of the part/material",
        quantity="How many to give or remove"
    )
    async def part(
        self,
        interaction: discord.Interaction,
        action: Literal["give", "remove"],
        user: discord.Member,
        item: str,
        quantity: int
    ):
        try:
            await interaction.response.defer(ephemeral=True)
            print(f"📥 /part: {interaction.user.display_name} {action} {quantity}×{item} → {user.display_name}")

            if quantity <= 0:
                await interaction.followup.send("⚠️ Quantity must be greater than **0**.", ephemeral=True)
                return

            item = item.strip()
            valid_parts = await self.get_all_parts()
            if item not in valid_parts:
                await interaction.followup.send(
                    f"❌ Invalid part.\nChoose from: {', '.join(valid_parts)}",
                    ephemeral=True
                )
                return

            profiles = await load_file(USER_DATA) or {}
            uid = str(user.id)
            profile = profiles.get(uid, {})
            stash = profile.get("stash", [])

            if not isinstance(stash, list):
                stash = []

            # ── Give ───────────────────────
            if action == "give":
                stash.extend([item] * quantity)
                msg = f"✅ Gave **{quantity} × {item}** to {user.mention}."

            # ── Remove ─────────────────────
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
            print(f"❌ Error in /part command: {type(e).__name__}: {e}")
            try:
                await interaction.followup.send(f"❌ Unexpected error: {e}", ephemeral=True)
            except:
                pass

    @part.autocomplete("item")
    async def autocomplete_item(self, interaction: discord.Interaction, current: str):
        all_parts = await self.get_all_parts()
        return [
            app_commands.Choice(name=p, value=p)
            for p in all_parts if current.lower() in p.lower()
        ][:25]

async def setup(bot):
    await bot.add_cog(PartManager(bot))
