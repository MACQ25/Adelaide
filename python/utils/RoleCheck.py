import discord
from discord import app_commands


def role_check():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id == interaction.guild.owner_id:
            return True
        permitted_id = await interaction.client.get_cog("Database").get_assigned_role(interaction.guild_id)
        return (permitted_id is None) or any(role.id == permitted_id for role in interaction.user.roles)
    return app_commands.check(predicate)