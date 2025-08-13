# cogs/help.py — Slash /help command that lists all Warlab commands cleanly
# - Groups Player vs Admin commands
# - Uses the live app command tree so descriptions stay in sync
# - Respects admin role from config.json (admin commands shown only to admins)

import discord
from discord.ext import commands
from discord import app_commands
import json
import os

CONFIG_PATH = "config.json"

def _load_config():
    cfg = {
        "admin_role_id": None,
        "command_channel_id": None,
    }
    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
            # config.json stores IDs as strings in this repo
            cfg["admin_role_id"] = int(str(data.get("admin_role_id"))) if data.get("admin_role_id") else None
            cfg["command_channel_id"] = int(str(data.get("command_channel_id"))) if data.get("command_channel_id") else None
    except Exception:
        pass
    return cfg

CFG = _load_config()

# Fallback descriptions in case a command is missing a .description
FALLBACK_DESCRIPTIONS = {
    "register":        "Create your Warlab profile.",
    "rank":            "View rank, prestige & buy boosts.",
    "scavenge":        "Scavenge for random materials (cooldown applies).",
    "market":          "Browse today’s rotating market.",
    "blackmarket":     "Browse the current black market offers.",
    "rollblueprint":   "Roll for a new random blueprint (1 per prestige).",
    "craft":           "Craft an item from your unlocked blueprints.",
    "turnin":          "Submit a crafted item for rewards.",
    "labskins":        "Equip a visual theme for your lab (Prestige I required).",
    "fortify":         "Open fortification UI and choose reinforcement.",
    "stash":           "View your stash, coins, skins, and buildable items.",
    "leaderboard":     "Top 3: raids won, builds completed, coins held.",
    "listregistered":  "Show all currently registered players and progress.",
    "task":            "Complete your daily Warlab mission for rewards.",
    "raid":            "Attempt to raid another player.",

    # Admin
    "adjust":          "Admin: Give or take prestige ranks from a player.",
    "coin":            "Admin: Give or take coins from a player.",
    "blueprint":       "Admin: Give or remove blueprints from a player.",
    "part":            "Admin: Give or remove parts from a player.",
    "tool":            "Admin: Give or remove tools from a player.",
    "skin":            "Admin: Give or remove lab skins from a player.",
    "forceregister":   "Admin: Force-register a player manually.",
    "forceunregister": "Admin: Remove a player's profile.",
    "cleanchannel":    "Admin: Wipe WARLAB channel after confirmation.",
    "warlabbackup":    "Admin: Back up all Warlab data to archive channel.",
    "warlabnuke":      "Admin: Reset all Warlab player data (IRREVERSIBLE).",
}

ADMIN_COMMANDS = {
    "adjust","coin","blueprint","part","tool","skin",
    "forceregister","forceunregister","cleanchannel","warlabbackup","warlabnuke"
}

GETTING_STARTED = [
    "Use **/register** to create your profile.",
    "Run **/scavenge** to gather parts (cooldown applies).",
    "Check **/rank** for prestige and boosts.",
    "Visit **/market** and **/blackmarket** to spend coins.",
    "Unlock blueprints with **/rollblueprint**, then **/craft** and **/turnin**.",
    "Customize with **/labskins** and **/fortify**.",
    "See progress with **/stash** and **/leaderboard**."
]

class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _is_admin(self, member: discord.Member) -> bool:
        if member.guild_permissions.manage_guild:
            return True
        if CFG.get("admin_role_id"):
            role = discord.utils.get(member.roles, id=CFG["admin_role_id"])
            return role is not None
        return False

    def _gather_commands(self, guild: discord.Guild):
        """
        Return two ordered dicts of {name: description} for player and admin commands.
        Pulls from the live app command tree; fills gaps with FALLBACK_DESCRIPTIONS.
        """
        # In practice, tree is already copied to guild and synced by bot.py
        tree_cmds = self.bot.tree.get_commands(guild=guild)
        # When not available (edge race), also include global commands:
        if not tree_cmds:
            tree_cmds = self.bot.tree.get_commands()

        players = {}
        admins  = {}

        for cmd in sorted(tree_cmds, key=lambda c: c.name):
            if not isinstance(cmd, app_commands.Command):
                continue
            name = cmd.name
            desc = (cmd.description or "").strip()
            if not desc:
                desc = FALLBACK_DESCRIPTIONS.get(name, "No description provided.")

            # Bucket
            if name in ADMIN_COMMANDS or desc.lower().startswith("admin"):
                admins[name] = desc
            else:
                players[name] = desc

        # Ensure any missing known commands also show up
        for k, v in FALLBACK_DESCRIPTIONS.items():
            if k in ADMIN_COMMANDS and k not in admins:
                admins[k] = v
            if k not in ADMIN_COMMANDS and k not in players:
                players[k] = v

        return players, admins

    def _format_list(self, bucket: dict) -> str:
        lines = []
        for name, desc in sorted(bucket.items()):
            lines.append(f"</{name}:0> — {desc}")
        return "\n".join(lines) if lines else "*None found.*"

    @app_commands.command(name="help", description="Show all Warlab commands and what they do.")
    async def help(self, interaction: discord.Interaction):
        players, admins = self._gather_commands(interaction.guild)

        is_admin = self._is_admin(interaction.user)

        embed = discord.Embed(
            title="⚙️ Warlab — Command Reference",
            description="Everything you can do, in one place.",
        )
        embed.add_field(
            name="Getting Started",
            value="\n".join(f"• {s}" for s in GETTING_STARTED),
            inline=False
        )
        embed.add_field(
            name="Player Commands",
            value=self._format_list(players),
            inline=False
        )
        if is_admin:
            embed.add_field(
                name="Admin Commands",
                value=self._format_list(admins),
                inline=False
            )

        # Footer notes (channel rules / cooldown hints)
        notes = []
        if CFG.get("command_channel_id"):
            notes.append(f"Most commands are intended for <#{CFG['command_channel_id']}>.")
        notes.append("Some actions have cooldowns (e.g., /scavenge, /raid).")
        notes.append("Need help with a specific command? Try it and read the on-screen prompts.")
        embed.set_footer(text=" ".join(notes))

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
