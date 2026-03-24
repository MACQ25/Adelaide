import datetime

import discord
from discord.ext import commands
from discord.ext.commands import Context, Bot
from discord import app_commands, ui
from cogs.SchedulingInteractions import Event
from CalendarImageGen import draw

class ExternalCalendar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ext_event_creation(self, guild_id: int, user: discord.User, event: Event):
        db_access = self.bot.get_cog("Database")
        try:
            await db_access.save_event(guild_id, event)
        except Exception as e:
            print("exception found on listener")


    @app_commands.command(name="force_refresh", description="Forces a refresh of the pinned calendar")
    async def fr(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        img = await draw(date_object=datetime.date, guild_id=interaction.guild_id)
        await interaction.followup.send(file=discord.File(img, "Calendar.jpeg"))

async def setup(bot: commands.Bot):
    await bot.add_cog(ExternalCalendar(bot))