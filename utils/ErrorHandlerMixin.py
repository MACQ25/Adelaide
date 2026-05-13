import discord
from discord import app_commands

class ErrorHandlerMixin:
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("You don't have the required role!", ephemeral=True)