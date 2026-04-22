from __future__ import annotations

import discord
from discord.ext import commands
from discord import app_commands
from objects.Event import Event, format_dates
from objects.EventColorEnum import EventColor
from objects.EventSettingsUI import EventSettings
from datetime import datetime as dt

class SchedulingInteractions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.get_cog("Database")

    async def owned_events_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        owned = await self.db.get_by_user(interaction.guild_id, interaction.user.id)
        return [ app_commands.Choice(name=item, value=item) for item in owned if item.__contains__(current) or current.__len__() == 0]


    async def event_dates_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        evt_name = interaction.namespace.name
        scheduled = await self.db.get_by_class(interaction.guild_id, evt_name)

        scheduled = [ dt.strptime(val.get('date'), "%Y-%m-%d %H:%M:%S").date().strftime("%B %d of %Y")  for val in scheduled ]

        entered_dates = [d.strip() for d in interaction.namespace.dates.split(",")]
        registered_values = [str(i) for i, n in enumerate(scheduled) if n in entered_dates]
        confirmed = [scheduled[int(i)] for i in registered_values]
        query = next((x for x in entered_dates if x not in confirmed), None)

        # [ app_commands.Choice(name=str(item[1]), value=str(item[0])) for item in scheduled if str(item[1]).__contains__(current) or current.__len__() == 0 ]

        choices = []

        if len(registered_values) > 0:
            choices.append(app_commands.Choice(
                name=', '.join(confirmed),
                value=', '.join(registered_values)
            ))

        for ind, item in enumerate(scheduled):
            if item in confirmed or str(ind) in registered_values:
                continue

            if query and query not in item:
                continue

            if len(registered_values) > 0:
                full_value = f"{",".join(registered_values)}, {ind}"

                choices.append(app_commands.Choice(
                    name=f'{", ".join(confirmed)}, {item}',
                    value=full_value,
                ))
            else:
                choices.append(app_commands.Choice(
                    name=item,
                    value= str(ind)
                ))

        return choices


    @app_commands.command(name="check", description="helper function to check if database is currently available")
    async def check(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.db.ping()
        await interaction.followup.send("Done!", ephemeral=True)


    @app_commands.command(name="assign",
                          description="Assigns a discord channel to which the bot will publish scheduled events")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def assign_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        result_msg = ""
        send_update_out = False
        try:
            await self.db.save_assigned(interaction.guild.id, channel)
            result_msg = "Channel updated to {}".format(channel)
            send_update_out = True
        except Exception as e:
            result_msg = "Could not update to target channel"
        finally:
            await interaction.followup.send(result_msg, ephemeral=True)
            if send_update_out:
                await self.bot.get_cog("ExternalCalendar").update_calendar(interaction.guild.id, interaction)


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
        desc="A brief description of the event",
        mode="Frequency with which the event happens (picked is specific dates)",
        dates="Comma-separated list of dates in M-D format, if only D provided then current month will be assumed",
        color="Color with which you want the event to be associated (Calendar specific)",
        starts="Start time of event, in 24 hour format (Defaults to 7 p.m)",
        duration="Duration of event in hours (Defaults to 4)"
    )
    async def create(self, interaction: discord.Interaction, name:str, dates:str, starts:int=19, duration:int=4, color: app_commands.Choice[str]=None, mode:int=1, desc:str=""):
        """Shows the settings view."""
        await interaction.response.defer(ephemeral=True)
        if not await self.db.check_if_exists(interaction.id, name):
            try:
                event = Event(
                    owner=interaction.user.id,
                    name=name,
                    description=desc,
                    colour=color,
                    mode=str(mode),
                    dates=dates,
                    starts=starts,
                    duration=duration
                )
                view = EventSettings(interaction.user, event)
                await interaction.followup.send(view=view, ephemeral=True)
            except TypeError:
                await interaction.followup.send(content="User didnt enter a number in one of the dates", ephemeral=True)
            except ValueError:
                await interaction.followup.send(content="User didnt enter a valid date amongst the provided ones", ephemeral=True)
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
        duration="Duration of event in hours (Defaults to 4)"
    )
    async def full_create(self, interaction: discord.Interaction, name:str, dates:str, starts:int=19, duration:int=4, color: app_commands.Choice[str]=None, mode:int=1, desc:str=""):
        await interaction.response.defer(ephemeral=True)
        if not await self.db.check_if_exists(interaction.id, name):
            try:
                event = Event(
                    owner=interaction.user.id,
                    name=name,
                    description=desc,
                    colour=color,
                    mode=str(mode),
                    dates=dates,
                    starts=starts,
                    duration=duration
                )
                view = EventSettings(interaction.user, event, True)
                await interaction.followup.send(view=view, ephemeral=True)
            except TypeError:
                await interaction.followup.send(content="User didnt enter a number in one of the dates", ephemeral=True)
            except ValueError:
                await interaction.followup.send(content="User didnt enter a valid date amongst the provided ones", ephemeral=True)
        else:
            await interaction.followup.send(content="Event already exists, pick a different name", ephemeral=True)


    @app_commands.command(name="cq", description="Schedules events based on pre-existing one from the user, skipping the modal")
    @app_commands.describe( name="The name of the event", dates="Comma-separated list of dates in M-D format, if only D provided then current month will be assumed" )
    @app_commands.autocomplete(name=owned_events_autocomplete)
    async def quick_create(self, interaction: discord.Interaction, name:str, dates:str):
        await interaction.response.defer(ephemeral=True)
        interaction.client.dispatch("ext_event_q_creation", interaction, name, format_dates(dates), 19, 4)


    @app_commands.command(name="fcq", description="Full Scheduling of an event the user owns, skips the modal")
    @app_commands.describe( name="The name of the event", dates="Comma-separated list of dates in M-D format, if only D provided then current month will be assumed", start_time="Start time of the event to create", duration="Duration of the event, in hours")
    @app_commands.autocomplete(name=owned_events_autocomplete)
    async def quick_full_create(self, interaction: discord.Interaction, name:str, dates:str, start_time:int=19, duration:int=4):
        await interaction.response.defer(ephemeral=True)
        interaction.client.dispatch("quick_creation", interaction, name, format_dates(dates, start_time), start_time, duration)


    @app_commands.command(name="cancel", description="Drops one or more scheduled dates for one specific event type")
    @app_commands.describe(
        name="The name of the event",
        dates="Comma-separated list of dates, empty will assume the closest date",
        all="Deletes all currently scheduled dates without setting it to inactive, overrides dates field"
    )
    @app_commands.autocomplete( name=owned_events_autocomplete, dates=event_dates_autocomplete )
    async def delete(self, interaction: discord.Interaction, name:str, dates:str="", all:bool=False):
        await interaction.response.defer(ephemeral=True)
        interaction.client.dispatch("ext_event_cancellation", interaction, name, dates.split(","), all)


    @app_commands.command(name="hiatus", description="Drops all forthcoming dates for the entered event and sets it as inactive")
    @app_commands.describe(name="Name of event class, so long cowboy", status="What is its status? (False = Hiatus)")
    @app_commands.autocomplete(name=owned_events_autocomplete)
    async def hiatus(self, interaction: discord.Interaction, name:str, status:bool):
        await interaction.response.defer(ephemeral=True)
        interaction.client.dispatch("ext_event_hiatus", interaction, name, status)


    @app_commands.command(name="delete", description="deletes all associated information to one given event, data, dates, etc")
    @app_commands.describe(name="Name The Victim")
    @app_commands.autocomplete(name=owned_events_autocomplete)
    async def full_delete(self, interaction: discord.Interaction, name:str):
        await interaction.response.defer(ephemeral=True)
        interaction.client.dispatch("ext_event_full_clean", interaction, name)


async def setup(bot):
    await bot.add_cog(SchedulingInteractions(bot))
