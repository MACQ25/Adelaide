from __future__ import annotations

from zoneinfo import ZoneInfo

import discord
from discord.ext import commands
from discord import app_commands

from cogs.InternalEvents import process_image
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
        if not await self.db.check_if_exists(interaction.guild_id, name):
            try:
                event = Event(
                    owner=interaction.user.id,
                    name=name,
                    description="",
                    dates=dates,
                    starts=12,
                    duration=1,
                    mode=str(mode),
                    colour=[color.value] if color is not None else [None],
                )
                view = EventSettings(interaction.user, event)
                await view.build()
                await interaction.followup.send(view=view, ephemeral=True)
            except TypeError as e:
                print(e)
                await interaction.followup.send(content="User didn't enter a number in one of the dates", ephemeral=True)
            except ValueError as e:
                print(e)
                await interaction.followup.send(content="User didn't enter a valid date amongst the provided ones", ephemeral=True)
            except Exception as e:
                print(e)
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
        create_channel="For Scheduled Events set up, use existing or create new section?",
        image="Thumbnail to be used for scheduled events (jpg, jpeg and png are accepted)"
    )
    @app_commands.autocomplete(timezone=AutocompleteMixin.timezone_autocomplete)
    async def full_create(self, interaction: discord.Interaction, name:str, dates:str, starts:int=19, duration:int=4, timezone:str="", color: app_commands.Choice[str]=None, mode:int=1, desc:str="", create_channel:bool=False, image:discord.Attachment=None):
        await defer(interaction)
        if not await self.db.check_if_exists(interaction.guild_id, name):

            if image:
                try:
                    file_name, image_bytes = await process_image(image, interaction)
                except ValueError:
                    return

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
                    timezone=timezone,
                    image=(file_name, image_bytes) if image else None
                )
                view = EventSettings(interaction.user, event, True, create_channel)
                await view.build()
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
        evt_package = Event(interaction.user.id, name, "", format_dates(dates))
        interaction.client.dispatch("ext_event_q_creation", interaction.guild, evt_package, int_events_id=None, interaction=interaction)


    @app_commands.command(name="fcq", description="Full Scheduling of an event the user owns, skips the modal")
    @app_commands.describe( name="The name of the event", dates="Comma-separated list of dates in M-D format, if only D provided then current month will be assumed", start_time="Start time of the event to create", duration="Duration of the event, in hours")
    @app_commands.autocomplete(name=AutocompleteMixin.owned_events_autocomplete)
    async def quick_full_create(self, interaction: discord.Interaction, name:str, dates:str, start_time:int=19, duration:int=4, timezone:str=""):
        await defer(interaction)
        evt_package = Event(interaction.user.id, name, "", format_dates(dates, start_time, timezone), start_time, duration)
        interaction.client.dispatch("quick_creation", interaction.guild, evt_package, event_data=None, interaction=interaction)


    @app_commands.command(name="cancel", description="Drops one or more scheduled dates for one specific event type")
    @app_commands.describe(
        name="The name of the event",
        dates="Comma-separated list of dates, empty will assume the closest date",
        all="Deletes all currently scheduled dates without setting it to inactive, overrides dates field"
    )
    @app_commands.autocomplete( name=AutocompleteMixin.owned_events_autocomplete, dates=AutocompleteMixin.event_dates_autocomplete )
    async def delete(self, interaction: discord.Interaction, name:str, dates:str="", all:bool=False):
        await defer(interaction)
        if len(dates) == 0 and not all:
            interaction.followup.send("No dates were given, nor was it requested to delete everything")
        else:
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


    async def get_parsed_data(self, interaction: discord.Interaction, event_name):
        data, days = await self.db.get_target_event(interaction.guild_id, interaction.user.id, event_name)
        ev_data = Event(
            interaction.user.id,
            data.get("name"),
            data.get("desc"),
            [d.get("date").astimezone(ZoneInfo(d.get("timezone", {}).get("tz_name", "UTC"))) for d in days],
            mode=data.get("frequency", {}).get("mode"),
            colour=data.get("color")
        )

        if len(ev_data.color) > 1:
            ev_data.custom_set_1 = ev_data.color[0]
            ev_data.custom_set_2 = ev_data.color[1]
            ev_data.custom_gradient = ev_data.color[2]

        full_flag = False

        if any(key in data for key in ["channel", "role_id", "thumbnail", "members"]):
            full_flag = True
            ev_data.section = data.get("channel",  {}).get("section_id", None)
            ev_data.text_channel = data.get("channel",  {}).get("text_id", None)
            ev_data.voice_channel = data.get("channel",  {}).get("vc_id", None)
            ev_data.role = data.get("role_id")
            ev_data.is_private = data.get("is_private", False)
            ev_data.members = [interaction.guild.get_member(m) for m in data.get("members", [])]
            ev_data.duration = data.get("frequency", {}).get("sample", {}).get("duration")

        return ev_data, full_flag


    @app_commands.command(name="update", description="allows you to update the data associated with a particular event")
    @app_commands.describe(name="name of the target event")
    @app_commands.autocomplete(name=AutocompleteMixin.owned_events_autocomplete)
    async def update_event(self,  interaction: discord.Interaction, name: str):
        await defer(interaction)
        event, full_flag = await self.get_parsed_data(interaction, name)
        view = EventSettings(interaction.user, event, full_flag, update_mode=True)
        await view.build()
        await interaction.followup.send(view=view, ephemeral=True)


    @app_commands.command(name="upgrade", description="upgrades a simple event to a full one, with channels and a role")
    @app_commands.describe(name="name of the target event")
    @app_commands.autocomplete(name=AutocompleteMixin.owned_basics_autocomplete)
    async def update_to_full(self, interaction: discord.Interaction, name: str):
        await defer(interaction)
        event, full_flag = await self.get_parsed_data(interaction, name)
        view = EventSettings(interaction.user, event, True, update_mode=True)
        await view.build()
        await interaction.followup.send(view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(SchedulingInteractions(bot))