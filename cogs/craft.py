# cogs/craft.py — Blueprint crafting with persistent storage + debug logging

import discord
from discord.ext import commands
from discord import app_commands
from collections import Counter

from utils.fileIO import load_file, save_file
from utils.inventory import has_required_parts, remove_parts
from utils.prestigeBonusHandler import can_craft_tactical, can_craft_explosives
from utils.prestigeUtils import apply_prestige_xp, broadcast_prestige_announcement, PRESTIGE_TIERS

USER_DATA       = "data/user_profiles.json"
RECIPE_DATA     = "data/item_recipes.json"
ARMOR_DATA      = "data/armor_blueprints.json"
EXPLOSIVE_DATA  = "data/explosive_blueprints.json"

TURNIN_ELIGIBLE = [
    "Mlock", "M4", "Mosin", "USG45", "BK-133",
    "Improvised Explosive Device", "Claymore", "Flashbang", "Frag Grenade",
    "Combat Outfit", "Tactical Outfit", "NBC Suit", "Humvee"
]

class CraftButton(discord.ui.Button):
    def __init__(self, user_id, blueprint, enabled=True):
        self.user_id = user_id
        self.blueprint = blueprint
        label = f"🛠️ {blueprint}"
        super().__init__(
            label=label,
            style=discord.ButtonStyle.success if enabled else discord.ButtonStyle.secondary,
            disabled=not enabled
        )

    async def callback(self, interaction: discord.Interaction):
        print(f"🔘 [CraftButton] Clicked for {self.blueprint} by {interaction.user.id}")
        await interaction.response.defer(ephemeral=True)

        if str(interaction.user.id) != self.user_id:
            await interaction.followup.send("⚠️ This isn’t your crafting menu.", ephemeral=True)
            return

        try:
            profiles   = await load_file(USER_DATA) or {}
            recipes    = await load_file(RECIPE_DATA) or {}
            armor      = await load_file(ARMOR_DATA) or {}
            explosives = await load_file(EXPLOSIVE_DATA) or {}
        except Exception as e:
            print(f"❌ [CraftButton] Failed to load data: {e}")
            await interaction.followup.send("❌ Error loading crafting data.", ephemeral=True)
            return

        all_recipes = {**recipes, **armor, **explosives}
        user = profiles.get(self.user_id)

        if not user:
            await interaction.followup.send("❌ User profile not found.", ephemeral=True)
            print(f"❌ [CraftButton] Profile not found: {self.user_id}")
            return

        blueprint_name = f"{self.blueprint} Blueprint"
        if blueprint_name not in user.get("blueprints", []):
            await interaction.followup.send(f"🔒 You must unlock **{blueprint_name}** first.", ephemeral=True)
            return

        item_key = self.blueprint.lower()
        recipe = all_recipes.get(item_key)
        if not recipe or not isinstance(recipe, dict):
            await interaction.followup.send("❌ Invalid blueprint data.", ephemeral=True)
            return

        prestige = user.get("prestige", 0)
        if item_key in armor and not can_craft_tactical(prestige):
            await interaction.followup.send("🔒 Requires Prestige II for tactical gear.", ephemeral=True)
            return
        if item_key in explosives and not can_craft_explosives(prestige):
            await interaction.followup.send("🔒 Requires Prestige III for explosives.", ephemeral=True)
            return

        stash = Counter(user.get("stash", []))
        if not has_required_parts(stash, recipe["requirements"]):
            missing = [
                f"{qty - stash.get(p, 0)}× {p}"
                for p, qty in recipe["requirements"].items()
                if stash.get(p, 0) < qty
            ]
            await interaction.followup.send("❌ Missing parts:\n• " + "\n• ".join(missing), ephemeral=True)
            return

        try:
            # Remove required parts
            remove_parts(stash, recipe["requirements"])
            
            # Then consume optional parts
            optional_parts = recipe.get("optional", {})
            optional_used = []
            for part, qty in optional_parts.items():
                if stash.get(part, 0) >= qty:
                    stash[part] -= qty
                    if stash[part] <= 0:
                        del stash[part]
                    optional_used.append(f"{qty}× {part}")
            
            # Update stash after consuming all parts
            user["stash"] = list(stash.elements())

            crafted = recipe["produces"]
            user["stash"].append(crafted)
            if crafted in TURNIN_ELIGIBLE:
                user.setdefault("crafted", []).append({
                    "item": crafted,
                    "optional": optional_used
                })
            
            user["builds_completed"] = user.get("builds_completed", 0) + 1
            user, ranked_up, rank_up_msg, old_rank, new_rank = apply_prestige_xp(user, xp_gain=25)
            
            # Save updated profile
            profiles[self.user_id] = user
            await save_file(USER_DATA, profiles)
            
            # Broadcast if rank-up occurred
            if ranked_up:
                await broadcast_prestige_announcement(interaction.client, interaction.user, user)

            print(f"🧪 [CraftButton] Crafted: {crafted} — XP applied — Saved profile: {self.user_id}")

            embed = discord.Embed(
                title="✅ Crafting Successful",
                description=f"You crafted **{crafted}**!",
                color=0x2ecc71
            )
            embed.add_field(name="Type", value=recipe.get("type", "Unknown"), inline=True)
            embed.add_field(name="Rarity", value=recipe.get("rarity", "Common"), inline=True)

            if optional_used:
                embed.add_field(name="Optional Bonuses", value="\n• " + "\n• ".join(optional_used), inline=False)

            prestige_rank = user.get("prestige", 0)
            prestige_points = user.get("prestige_points", 0)
            next_threshold = PRESTIGE_TIERS.get(prestige_rank + 1, None)
            if next_threshold:
                embed.add_field(name="🧬 Prestige", value=f"{prestige_rank} — {prestige_points}/{next_threshold}", inline=False)
            else:
                embed.add_field(name="🧬 Prestige", value=f"{prestige_rank} — MAX", inline=False)

            if ranked_up and rank_up_msg:
                embed.description += f"\n{rank_up_msg}"

            embed.set_footer(text="WARLAB | SV13 Bot")
            await self.view.stored_messages[0].edit(embed=embed)

            # UI refresh
            if hasattr(self.view, "stored_messages"):
                updated_stash = Counter(user["stash"])
                updated_view = CraftView(self.user_id, user.get("blueprints", []), updated_stash, all_recipes)
                updated_view.stored_messages = self.view.stored_messages

                # Rebuild embed
                grouped = {"🔫 Weapons": [], "🪖 Armor": [], "💣 Explosives": []}
                for bp in user.get("blueprints", []):
                    core = bp.replace(" Blueprint", "").strip()
                    key = core.lower()
                    r = all_recipes.get(key)
                    if not r: continue
                    reqs = r.get("requirements", {})
                    if all(updated_stash.get(p, 0) >= q for p, q in reqs.items()):
                        line = f"{r['produces']} — ✅ Build Ready"
                    else:
                        missing = [
                            f"{q - updated_stash.get(p, 0)}× {p}"
                            for p, q in reqs.items()
                            if updated_stash.get(p, 0) < q
                        ]
                        line = f"{r['produces']} — ❌ Missing Parts:\n• " + "\n• ".join(missing)
                    if key in explosives:
                        grouped["💣 Explosives"].append(line)
                    elif key in armor:
                        grouped["🪖 Armor"].append(line)
                    else:
                        grouped["🔫 Weapons"].append(line)

                updated_embed = discord.Embed(
                    title="🔧 Blueprint Workshop (Updated)",
                    description="Click an item below to craft it if you have the parts.",
                    color=0xf1c40f
                )
                updated_embed.set_footer(text="WARLAB | SV13 Bot")
                updated_embed.add_field(name="📘 Blueprints Owned", value="\n".join(f"• {bp}" for bp in user.get("blueprints", [])), inline=False)
                for group_name, items in grouped.items():
                    if items:
                        updated_embed.add_field(name=group_name, value="\n".join(items), inline=False)

                await self.view.stored_messages[0].edit(embed=updated_embed, view=updated_view)

        except Exception as e:
            print(f"❌ [CraftButton] Exception occurred: {e}")
            try:
                await interaction.user.send("✅ Crafting succeeded, but view update failed.")
            except:
                pass

class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close", style=discord.ButtonStyle.danger, row=4)

    async def callback(self, interaction: discord.Interaction):
        print(f"❌ [CloseButton] Triggered by {interaction.user.id}")
        try:
            for child in self.view.children:
                child.disabled = True
            await interaction.response.edit_message(
                content="❌ Crafting view closed.",
                embed=None,
                view=None
            )
        except Exception as e:
            print(f"❌ [CloseButton] Failed to edit message: {e}")
            await interaction.followup.send("❌ Failed to close view. Try again or refresh.", ephemeral=True)

class CraftView(discord.ui.View):
    def __init__(self, user_id, blueprints, stash_counter, all_recipes):
        super().__init__(timeout=90)
        self.stored_messages = []
        count = 0
        for bp in blueprints:
            core_name = bp.replace(" Blueprint", "").strip()
            key = core_name.lower()
            recipe = all_recipes.get(key)
            if not recipe:
                continue
            reqs = recipe.get("requirements", {})
            can_build = all(stash_counter.get(p, 0) >= q for p, q in reqs.items())
            self.add_item(CraftButton(user_id, core_name, enabled=can_build))
            count += 1
            if count >= 20:
                break
        self.add_item(CloseButton())

class Craft(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="craft", description="Craft an item from your unlocked blueprints")
    async def craft(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        uid = str(interaction.user.id)
        print(f"🛠️ [Craft] Opening workshop for UID: {uid}")
        profiles = await load_file(USER_DATA) or {}
        recipes = await load_file(RECIPE_DATA) or {}
        armor = await load_file(ARMOR_DATA) or {}
        explosives = await load_file(EXPLOSIVE_DATA) or {}
        user = profiles.get(uid)

        if not user:
            await interaction.followup.send("❌ You don't have a profile yet. Use `/register` first.", ephemeral=True)
            return

        blueprints = user.get("blueprints", [])
        if not blueprints:
            await interaction.followup.send("🔒 You don’t own any blueprints. Visit `/blackmarket`.", ephemeral=True)
            return

        stash = Counter(user.get("stash", []))
        all_recipes = {**recipes, **armor, **explosives}
        grouped_buildables = {"🔫 Weapons": [], "🪖 Armor": [], "💣 Explosives": []}

        for bp in blueprints:
            core_name = bp.replace(" Blueprint", "").strip()
            key = core_name.lower()
            recipe = all_recipes.get(key)
            if not recipe:
                continue
            reqs = recipe.get("requirements", {})
            can_build = all(stash.get(p, 0) >= q for p, q in reqs.items())
            if can_build:
                line = f"{recipe['produces']} — ✅ Build Ready"
            else:
                missing = [
                    f"{q - stash.get(p, 0)}× {p}" 
                    for p, q in reqs.items() 
                    if stash.get(p, 0) < q
                ]
                line = f"{recipe['produces']} — ❌ Missing Parts:\n• " + "\n• ".join(missing)

            if key in explosives:
                grouped_buildables["💣 Explosives"].append(line)
            elif key in armor:
                grouped_buildables["🪖 Armor"].append(line)
            else:
                grouped_buildables["🔫 Weapons"].append(line)

        embed = discord.Embed(
            title=f"🔧 {interaction.user.display_name}'s Blueprint Workshop",
            description="Click an item below to craft it if you have the parts.",
            color=0xf1c40f
        )
        embed.set_footer(text="WARLAB | SV13 Bot")
        embed.add_field(
            name="📘 Blueprints Owned",
            value="\n".join(f"• {bp}" for bp in blueprints),
            inline=False
        )
        for group_name, items in grouped_buildables.items():
            if items:
                embed.add_field(name=group_name, value="\n".join(items), inline=False)

        view = CraftView(uid, blueprints, stash, all_recipes)
        msg = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        view.stored_messages = [await interaction.original_response()]

async def setup(bot):
    await bot.add_cog(Craft(bot))
