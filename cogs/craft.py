# cogs/craft.py — Dynamic blueprint crafting with part checks

import discord
from discord.ext import commands
from discord import app_commands
from utils.fileIO import load_file, save_file
from utils.inventory import has_required_parts, remove_parts
from utils.prestigeBonusHandler import can_craft_tactical, can_craft_explosives

USER_DATA = "data/user_profiles.json"
RECIPE_DATA = "data/item_recipes.json"

class Craft(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_owned_blueprints(self, user_id):
        profiles = await load_file(USER_DATA) or {}
        recipes = await load_file(RECIPE_DATA) or {}
        user = profiles.get(user_id, {})
        owned = user.get("blueprints", [])
        return [bp for bp in owned if bp.replace(" Blueprint", "").lower() in recipes]

    @app_commands.command(name="craft", description="Craft an item using a blueprint and parts.")
    @app_commands.describe(item="Select an unlocked blueprint to craft")
    async def craft(self, interaction: discord.Interaction, item: str):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        profiles = await load_file(USER_DATA) or {}
        recipes = await load_file(RECIPE_DATA) or {}

        user = profiles.get(user_id, {
            "stash": [],
            "blueprints": [],
            "prestige": 0,
            "crafted": [],
            "labskins": [],
            "equipped_skin": "default",
        })

        item_key = item.replace(" Blueprint", "").lower()
        recipe = recipes.get(item_key)

        if not recipe:
            await interaction.followup.send("❌ Unknown item or invalid blueprint selected.", ephemeral=True)
            return

        # ✅ Blueprint ownership check
        blueprint_name = f"{recipe['produces']} Blueprint"
        if blueprint_name not in user.get("blueprints", []):
            await interaction.followup.send(f"🔒 You must unlock **{blueprint_name}** before crafting this item.", ephemeral=True)
            return

        # 🧠 Prestige checks
        if "tactical" in item_key and not can_craft_tactical(user.get("prestige", 0)):
            await interaction.followup.send("🔒 Requires Prestige II to craft tactical gear.", ephemeral=True)
            return
        if "explosive" in item_key and not can_craft_explosives(user.get("prestige", 0)):
            await interaction.followup.send("🔒 Requires Prestige III to craft explosives or special items.", ephemeral=True)
            return

        # 🔧 Parts check
        if not has_required_parts(user["stash"], recipe["requirements"]):
            missing_parts = []
            for part, qty in recipe["requirements"].items():
                owned = user["stash"].count(part)
                if owned < qty:
                    missing_parts.append(f"{qty - owned}x {part}")
            await interaction.followup.send(
                f"❌ You’re missing the following parts:\n• " + "\n• ".join(missing_parts),
                ephemeral=True
            )
            return

        # ✅ Crafting logic
        remove_parts(user["stash"], recipe["requirements"])
        crafted_item = recipe["produces"]
        user["stash"].append(crafted_item)
        user.setdefault("crafted", []).append(crafted_item)
        profiles[user_id] = user
        await save_file(USER_DATA, profiles)

        # 🎉 Success response
        embed = discord.Embed(
            title="✅ Crafting Successful",
            description=f"You crafted **{crafted_item}**!",
            color=0x2ecc71
        )
        embed.add_field(name="Type", value=recipe.get("type", "Unknown"), inline=True)
        embed.add_field(name="Rarity", value=recipe.get("rarity", "Common"), inline=True)
        embed.set_footer(text="WARLAB | SV13 Bot")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @craft.autocomplete("item")
    async def craft_autocomplete(self, interaction: discord.Interaction, current: str):
        user_id = str(interaction.user.id)
        options = await self.get_owned_blueprints(user_id)
        return [
            app_commands.Choice(name=bp, value=bp)
            for bp in options if current.lower() in bp.lower()
        ][:25]

async def setup(bot):
    await bot.add_cog(Craft(bot))
