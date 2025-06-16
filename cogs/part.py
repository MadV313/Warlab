# cogs/part.py — Admin: Give or remove parts from a player (flat stash format)

import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
GUN_PARTS = "data/item_recipes.json"
ARMOR_PARTS = "data/armor_blueprints.json"
EXPLOSIVE_PARTS = "data/explosive_blueprints.json"

class PartManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_all_parts(self):
        guns = await load_file(GUN_PARTS) or {}
        armors = await load_file(ARMOR_PARTS) or {}
        explosives = await load_file(EXPLOSIVE_PARTS) or {}
        categorized = {}

        for source, label in [(guns, "Weapons"), (armors, "Armor"), (explosives, "Explosives")]:
            for item in source.values():
                for part in item.get("required_parts", []):
                    categorized[f"[{label}] {part}"] = part  # Display name → real name

        return categorized

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

            all_parts = await self.get_all_parts()
            part_lookup = {v: k for k, v in all_parts.items()}  # Reverse for validation

            if item not in part_lookup:
                await interaction.followup.send(
                    f"❌ Invalid part.\nValid choices: {', '.join(sorted(set(all_parts.values())))}",
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
        results = [
            app_commands.Choice(name=display_name, value=real_name)
            for display_name, real_name in all_parts.items()
            if current.lower() in display_name.lower()
        ]
        return results[:25]

async def setup(bot):
    await bot.add_cog(PartManager(bot))
