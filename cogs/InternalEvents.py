import discord
from discord.ext import commands
from discord.ext.commands import Context, Bot
from discord import app_commands, ui

class InternalEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── Slash Commands ──────────────────────────────────────────

    @app_commands.command(name="hello", description="Says hello.")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Hello, {interaction.user.mention}!")


# ── Setup ───────────────────────────────────────────────────────

async def setup(bot: commands.Bot):
    await bot.add_cog(InternalEvents(bot))