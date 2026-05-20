import discord


async def defer(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)  # type: ignore[attr-defined]