# cogs/part.py — Remote Part Give/Remove with Debug + Master Reference Lookup + Validated Removals

import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from utils.fileIO import load_file, save_file

USER_DATA = "data/user_profiles.json"
PART_MASTER_REF = "data/part_master_reference.json"

class PartManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cached_parts = {}  # {"Weapons": [...], "Armor": [...], "Explosives": [...]}

    async def get_parts_by_category(self, category):
        if category in self.cached_parts:
            return self.cached_parts[category]

        ref = await load_file(PART_MASTER_REF) or {}
        self.cached_parts[category] = ref.get(category, [])
        print(f"📦 [part.py] Cached parts for {category}: {self.cached_parts[category]}")
        return self.cached_parts[category]

    @app_commands.command(name="part", description="Admin: Give or remove parts from a player.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        action="Give or remove a part",
        user="Target player",
        item="Category: Weapons, Armor, or Explosives",
        part="Part name from selected category",
        quantity="Amount to give or remove"
    )
    async def part(
        self,
        interaction: discord.Interaction,
        action: Literal["give", "remove"],
        user: discord.Member,
        item: Literal["Weapons", "Armor", "Explosives"],
        part: str,
        quantity: int
    ):
        await interaction.response.defer(ephemeral=True)
        uid = str(user.id)

        print(f"📥 [part.py] /part used by {interaction.user} — {action} {quantity}x {part} to {user} ({uid})")

        if quantity <= 0:
            await interaction.followup.send("⚠️ Quantity must be greater than 0.", ephemeral=True)
            return

        valid_parts = await self.get_parts_by_category(item)
        if part not in valid_parts:
            print(f"❌ [part.py] Invalid part '{part}' for category '{item}'")
            await interaction.followup.send(
                f"❌ Invalid part for {item}. Try auto-completing the field.",
                ephemeral=True
            )
            return

        profiles = await load_file(USER_DATA) or {}

        if uid not in profiles:
            print(f"❌ [part.py] No profile found for {uid}")
            await interaction.followup.send(
                f"❌ That player does not have a profile yet. Ask them to use `/register` first.",
                ephemeral=True
            )
            return

        profile = profiles[uid]
        stash = profile.get("stash", [])
        if not isinstance(stash, list):
            stash = []

        # ── Action Logic ──
        if action == "give":
            stash.extend([part] * quantity)
            msg = f"✅ Gave **{quantity} × {part}** to {user.mention}."
            print(f"🎁 [part.py] Gave {quantity}x {part} to {uid}")
        else:
            if stash.count(part) < quantity:
                msg = f"⚠️ {user.mention} does not have **{quantity} × {part}** to remove."
                print(f"❌ [part.py] Not enough {part} to remove from {user.display_name}")
                await interaction.followup.send(msg, ephemeral=True)
                return

            removed = 0
            new_stash = []
            for s in stash:
                if s == part and removed < quantity:
                    removed += 1
                    continue
                new_stash.append(s)

            stash = new_stash
            msg = f"🗑 Removed **{removed} × {part}** from {user.mention}."
            print(f"🧹 [part.py] Removed {removed}/{quantity}x {part} from {uid}")

        profile["stash"] = stash
        profiles[uid] = profile
        await save_file(USER_DATA, profiles)

        print(f"💾 [part.py] Updated stash saved for user {uid}")
        await interaction.followup.send(msg, ephemeral=True)

    @part.autocomplete("part")
    async def autocomplete_part(self, interaction: discord.Interaction, current: str):
        item_category = interaction.namespace.item
        if not item_category:
            return []

        parts = await self.get_parts_by_category(item_category)
        return [
            app_commands.Choice(name=p, value=p)
            for p in parts if current.lower() in p.lower()
        ][:25]

async def setup(bot):
    await bot.add_cog(PartManager(bot))
