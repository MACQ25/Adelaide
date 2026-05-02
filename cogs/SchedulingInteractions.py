from __future__ import annotations

import discord
from discord.ext import commands
from discord import app_commands
from objects.AutocompleteMixin import AutocompleteMixin
from objects.Event import Event, format_dates
from objects.EventColorEnum import EventColor
from objects.EventSettingsUI import EventSettings
import zoneinfo


async def defer(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)  # type: ignore[attr-defined]


class SchedulingInteractions(AutocompleteMixin, commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.get_cog("Database")
        self.setup_db(self.bot)


    @app_commands.command(name="check", description="helper function to check if database is currently available")
    async def check(self, interaction: discord.Interaction):
        await defer(interaction)
        await self.db.ping()
        await interaction.followup.send("Done!", ephemeral=True)


    @app_commands.command(name="create", description="opens modal for event creation")
    @app_commands.choices(
        color=[c.as_choice() for c in EventColor],
        mode=[
            app_commands.Choice(name="picked", value=1),
            app_commands.Choice(name="weekly", value=2),
            app_commands.Choice(name="monthly", value=3),
        ]
    )
    @app_commands.describe(
        name="The name of the event",
        mode="Frequency with which the event happens (picked is specific dates)",
        dates="Comma-separated list of dates in M-D format, if only D provided then current month will be assumed",
        color="Color with which you want the event to be associated (Calendar specific)"
    )
    async def create(self, interaction: discord.Interaction, name:str, dates:str, color: app_commands.Choice[str]=None, mode:int=1):
        """Shows the settings view."""
        await defer(interaction)
        if not await self.db.check_if_exists(interaction.id, name):
            try:
                event = Event(
                    owner=interaction.user.id,
                    name=name,
                    description="",
                    colour=[color.value] if color is not None else [None],
                    mode=str(mode),
                    dates=dates,
                    starts=19,
                    duration=4
                )
                view = EventSettings(interaction.user, event)
                await interaction.followup.send(view=view, ephemeral=True)
            except TypeError:
                await interaction.followup.send(content="User didn't enter a number in one of the dates", ephemeral=True)
            except ValueError:
                await interaction.followup.send(content="User didn't enter a valid date amongst the provided ones", ephemeral=True)
        else:
            await interaction.followup.send(content="Event already exists, pick a different name", ephemeral=True)


    @app_commands.command(name="full-create", description="opens modal for event creation")
    @app_commands.choices(
        color=[c.as_choice() for c in EventColor],
        mode=[
            app_commands.Choice(name="picked", value=1),
            app_commands.Choice(name="weekly", value=2),
            app_commands.Choice(name="monthly", value=3),
        ]
    )
    @app_commands.describe(
        name="The name of the event",
        desc="A brief description of the event",
        mode="Frequency with which the event happens (picked is specific dates)",
        dates="Comma-separated list of dates in M-D format, if only D provided then current month will be assumed",
        color="Color with which you want the event to be associated (Calendar specific)",
        starts="Start time of event, in 24 hour format (Defaults to 7 p.m)",
        duration="Duration of event in hours (Defaults to 4)",
        timezone="Your current timezone",
        create_channel="For Scheduled Events set up, use existing or create new section?"
    )
    async def full_create(self, interaction: discord.Interaction, name:str, dates:str, starts:int=19, duration:int=4, timezone:str="", color: app_commands.Choice[str]=None, mode:int=1, desc:str="", create_channel:bool=False):
        await defer(interaction)
        if not await self.db.check_if_exists(interaction.id, name):
            try:
                event = Event(
                    owner=interaction.user.id,
                    name=name,
                    description=desc,
                    colour=[color.value] if color is not None else [None],
                    mode=str(mode),
                    dates=dates,
                    starts=starts,
                    duration=duration,
                    timezone=timezone
                )
                view = EventSettings(interaction.user, event, True, create_channel)
                await interaction.followup.send(view=view, ephemeral=True)
            except TypeError:
                await interaction.followup.send(content="User didn't enter a number in one of the dates", ephemeral=True)
            except ValueError:
                await interaction.followup.send(content="User didn't enter a valid date amongst the provided ones", ephemeral=True)
        else:
            await interaction.followup.send(content="Event already exists, pick a different name", ephemeral=True)


    @app_commands.command(name="cq", description="Schedules events based on pre-existing one from the user, skipping the modal")
    @app_commands.describe( name="The name of the event", dates="Comma-separated list of dates in M-D format, if only D provided then current month will be assumed" )
    @app_commands.autocomplete(name=AutocompleteMixin.owned_events_autocomplete)
    async def quick_create(self, interaction: discord.Interaction, name:str, dates:str):
        await defer(interaction)
        interaction.client.dispatch("ext_event_q_creation", interaction.guild, interaction.user.id, name, format_dates(dates), 19, 4, int_events_id=None, interaction=interaction)


    @app_commands.command(name="fcq", description="Full Scheduling of an event the user owns, skips the modal")
    @app_commands.describe( name="The name of the event", dates="Comma-separated list of dates in M-D format, if only D provided then current month will be assumed", start_time="Start time of the event to create", duration="Duration of the event, in hours")
    @app_commands.autocomplete(name=AutocompleteMixin.owned_events_autocomplete)
    async def quick_full_create(self, interaction: discord.Interaction, name:str, dates:str, start_time:int=19, duration:int=4, timezone:str=""):
        await defer(interaction)
        interaction.client.dispatch("quick_creation", interaction.guild, interaction.user.id, name, format_dates(dates, start_time), start_time, duration, event_data=None, interaction=interaction)


    @app_commands.command(name="cancel", description="Drops one or more scheduled dates for one specific event type")
    @app_commands.describe(
        name="The name of the event",
        dates="Comma-separated list of dates, empty will assume the closest date",
        all="Deletes all currently scheduled dates without setting it to inactive, overrides dates field"
    )
    @app_commands.autocomplete( name=AutocompleteMixin.owned_events_autocomplete, dates=AutocompleteMixin.event_dates_autocomplete )
    async def delete(self, interaction: discord.Interaction, name:str, dates:str="", all:bool=False):
        await defer(interaction)
        interaction.client.dispatch("ext_event_cancellation", interaction, name, dates.split(","), all)


    @app_commands.command(name="hiatus", description="Drops all forthcoming dates for the entered event and sets it as inactive")
    @app_commands.describe(name="Name of event class, so long cowboy", status="What is its status? (False = Hiatus)")
    @app_commands.autocomplete(name=AutocompleteMixin.owned_events_autocomplete)
    async def hiatus(self, interaction: discord.Interaction, name:str, status:bool):
        await defer(interaction)
        interaction.client.dispatch("ext_event_hiatus", interaction, name, status)


    @app_commands.command(name="delete", description="deletes all associated information to one given event, data, dates, etc")
    @app_commands.describe(name="Name The Victim")
    @app_commands.autocomplete(name=AutocompleteMixin.owned_events_autocomplete)
    async def full_delete(self, interaction: discord.Interaction, name:str):
        await defer(interaction)
        interaction.client.dispatch("ext_event_full_clean", interaction, name)


async def setup(bot):
    await bot.add_cog(SchedulingInteractions(bot))
