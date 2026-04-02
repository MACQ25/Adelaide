from __future__ import annotations

import discord
from discord.ext import commands
from discord.ext.commands import Context, Bot
from discord import app_commands, ui
import datetime as dt
import enum

class EventColor(enum.Enum):
    red      = discord.Color.red()
    blue     = discord.Color.blue()
    green    = discord.Color.green()
    orange   = discord.Color.orange()
    purple   = discord.Color.purple()
    yellow   = discord.Color.yellow()
    white    = discord.Color.light_theme()
    black    = discord.Color.dark_theme()

    @property
    def emoji(self) -> str:
        emojis = {
            'red':     '🔴',
            'blue':    '🔵',
            'green':   '🟢',
            'orange':  '🟠',
            'purple':  '🟣',
            'yellow':  '🟡',
            'white':   '⬜',
            'black': '⬛',
        }
        return emojis[self.name]

    def as_choice(self) -> app_commands.Choice:
        return app_commands.Choice(name=f"{self.emoji} {self.name.capitalize()}", value=str(self.value))

    def as_option(self) -> discord.SelectOption:
        return discord.SelectOption(label=self.name.capitalize(), emoji=self.emoji, value=str(self.value))


def format_dates(dates:str, start_time:int=19):
    date_list = dates.split(",")
    current = dt.datetime.now()
    for i, d in enumerate(date_list):
        try:
            spl = [int(itm.strip()) for itm in d.split("-")]
            if len(spl) == 1:
                date_stamp = dt.datetime(current.year, current.month, spl[0], hour=start_time)
            elif len(spl) == 2:
                date_stamp = dt.datetime(current.year, spl[0], spl[1], hour=start_time)
            else:
                date_stamp = dt.datetime(spl[0], spl[1], spl[2], hour=start_time)
            date_list[i] = date_stamp.__str__()
        except TypeError:
            raise TypeError()
        except ValueError:
            raise ValueError()
    return date_list


class Event:

    def __init__(self, owner:int, name:str, description:str, colour:str, mode:str, dates:str, starts:int, duration:int, location:str = "The Interwebs",
                 recurrence: tuple = tuple(), attendees: tuple = tuple()):
        # Unique information saved on its own folder, relational style
        self.owner = owner

        # Individual information saved also on its own folder
        self.summary = name
        self.description = description
        self.location = location
        # Saved on the above folder, divided because these are important to be reflected on the calendar
        self.color = colour
        self.frequency = mode

        # Saved on a general ID tracked list of dates, based on server
        self.dates = format_dates(dates, start_time=starts)
        self.starts = starts
        self.duration = duration

        # Vestigial, ignore them until further notice
        # self.recurrence = recurrence
        # self.attendees = attendees


    def __str__(self):
        return (f"Owner: {self.owner}, Summary: {self.summary}, "
                f"Location: {self.location}, Description: {self.description}, Color: {self.color}, "
                f"Frequency: {self.frequency}, Dates: {self.dates}, Starts: {self.starts}, Duration: {self.duration}, "
                f"Recurrence: {self.recurrence}, Attendees: {self.attendees}")


class TextModal(ui.Modal, title="Modal Title"):
    nameInput = ui.TextInput(style=discord.TextStyle.paragraph, required=True)

    def __init__(self, view: 'EventSettings', button: SetTextButton):
        super().__init__()
        if button.mode:
            self.title = "Set the event name"
            self.nameInput.label = 'New Name'
            self.nameInput.default = 'Papus Incredible Adventure'
        else:
            self.title = "Write a description"
            self.nameInput.label = 'New Description'
            self.nameInput.default = 'A very useful description'

        self.view = view
        self.values = view.data
        self.button = button

    async def on_submit(self, interaction: discord.Interaction[Bot]) -> None:
        try:
            if self.button.mode:
                self.values.summary = str(self.nameInput.value)
                self.button.label = str(self.values.summary)
            else:
                self.values.description = str(self.nameInput.value)
            await interaction.response.edit_message(view=self.view)
        except ValueError:
            await interaction.response.send_message('Something Went Wrong.', ephemeral=True)


class SetTextButton(ui.Button['EventSettings']):
    def __init__(self, values: Event, mode:bool):
        super().__init__(
            label=str(values.summary if values.summary.isalpha() else "Set a title") if mode else "Desc",
            style=discord.ButtonStyle.secondary
        )
        self.values = values
        self.mode = mode


    async def callback(self, interaction: discord.Interaction[Bot]) -> None:
        # Tell the type checker that a view is attached already
        assert self.view is not None
        await interaction.response.send_modal(TextModal(self.view, self))


class ColorSetting(ui.ActionRow['EventSettings']):
    def __init__(self, values: Event):
        super().__init__()
        self.values = values
        self.update_options()

    def update_options(self):
        for option in self.select_color.options:
            option.default = option.value == self.values.color

    @ui.select(placeholder='Select a color', options=[color.as_option() for color in EventColor])
    async def select_color(self, interaction: discord.Interaction[Bot], select: discord.ui.Select) -> None:
        self.values.color = select.values[0]
        self.update_options()
        await interaction.response.edit_message(view=self.view)


class FrequencySelect(ui.ActionRow['EventSettings']):
    def __init__(self, values: Event):
        super().__init__()
        self.values = values
        self.update_frequency()

    def update_frequency(self):
        for option in self.select_mode.options:
            option.default = option.value == self.values.frequency

    @ui.select(
        placeholder='Select the frequency',
        options=[
            discord.SelectOption(label="Picked", description="the event will occur on a given set of days", value=str(1)),
            discord.SelectOption(label="Weekly", description="the event will occur every week at a given hour", value=str(2)),
            discord.SelectOption(label="Monthly", description="the event will occur every month at a given hour", value=str(3))
        ]
    )
    async def select_mode(self, interaction: discord.Interaction[Bot], select: discord.ui.Select) -> None:
        self.values.frequency = select.values[0]
        self.update_frequency()
        await interaction.response.edit_message(view=self.view)


class DatesModal(ui.Modal, title="Modal Title"):
    datesInput = ui.TextInput(label="dates", style=discord.TextStyle.paragraph, required=True)

    def __init__(self, view: 'EventSettings', button: SetDatesButton):
        super().__init__()
        self.view = view
        self.values = view.data
        self.button = button
        date_string = ""
        for date in self.values.dates:
            date_string += date + ",\n"
        self.datesInput.default = date_string

    async def on_submit(self, interaction: discord.Interaction[Bot]) -> None:
        try:
            self.values.dates = [d.strip() for d in self.datesInput.value.split(",") if d.strip()]
            await interaction.response.edit_message(view=self.view)
        except ValueError:
            await interaction.response.send_message('Something Went Wrong.', ephemeral=True)


class SetDatesButton(ui.Button['EventSettings']):
    def __init__(self, values: Event):
        super().__init__(
            label="📆",
            style=discord.ButtonStyle.secondary
        )
        self.values = values

    async def callback(self, interaction: discord.Interaction[Bot]) -> None:
        # Tell the type checker that a view is attached already
        assert self.view is not None
        await interaction.response.send_modal(DatesModal(self.view, self))


class DurationModal(ui.Modal, title='Set hours count'):
    count = ui.TextInput(label='Count', style=discord.TextStyle.short, default='4', required=True)

    def __init__(self, view: 'EventSettings', button: SetCountButton):
        super().__init__()
        self.view = view
        self.values = view.data
        self.button = button

    async def on_submit(self, interaction: discord.Interaction[Bot]) -> None:
        try:
            self.values.duration = int(self.count.value)
            self.button.label = str(self.values.duration)
            await interaction.response.edit_message(view=self.view)
        except ValueError:
            await interaction.response.send_message('Invalid count. Please enter a number.', ephemeral=True)


class SetCountButton(ui.Button['EventSettings']):
    def __init__(self, values: Event):
        super().__init__(label=str(values.duration), style=discord.ButtonStyle.secondary)
        self.values = values

    async def callback(self, interaction: discord.Interaction[Bot]) -> None:
        # Tell the type checker that a view is attached already
        assert self.view is not None
        await interaction.response.send_modal(DurationModal(self.view, self))


class EventSettings(ui.LayoutView):

    row = ui.ActionRow()

    def __init__(self, data:Event):
        super().__init__()
        self.data = data


        print(self.data.frequency, self.data.dates)

        # For this example, we'll use multiple sections to organize the settings.
        container = ui.Container()
        header = ui.TextDisplay('# Settings\n-# This is an example to showcase how to do settings.')
        container.add_item(header)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))

        self.event_name_btn = SetTextButton(self.data, True)
        container.add_item(
            ui.Section(
                ui.TextDisplay('## Event Name\n-# The name to be saved to the discord UI.'),
                accessory=self.event_name_btn,
            )
        )

        self.event_desc_btn = SetTextButton(self.data, False)
        container.add_item(
            ui.Section(
                ui.TextDisplay('## Description\n-# Extra details to be saved to UI.'),
                accessory=self.event_desc_btn,
            )
        )

        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(ui.TextDisplay('## Color Selection\n-# This is the color that is shown in the calendar image.'))
        container.add_item(ColorSetting(self.data))

        self.event_dates_btn = SetDatesButton(self.data)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(
            ui.Section(
                ui.TextDisplay('## Date Information\n-# Days and hours in which the event will happen.'),
                accessory=self.event_dates_btn
            )
        )
        container.add_item(FrequencySelect(self.data))

        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.count_button = SetCountButton(self.data)
        container.add_item(
            ui.Section(
                ui.TextDisplay('## Event Duration\n-# This is the number of hours the event will last (only reflected in discord UI).'),
                accessory=self.count_button,
            )
        )

        self.add_item(container)

        # Swap the row so it's at the end
        self.remove_item(self.row)
        self.add_item(self.row)


    @row.button(label='Finish', style=discord.ButtonStyle.green)
    async def finish_button(self, interaction: discord.Interaction[Bot], button: ui.Button) -> None:
        # Edit the message to make it the interaction response...
        await interaction.response.edit_message(view=self)
        # ...and then send a confirmation message.
        await interaction.followup.send(f'Settings saved.', ephemeral=True)
        # Then delete the settings panel
        self.stop()
        interaction.client.dispatch("ext_event_creation", interaction, self.data)

        await interaction.delete_original_response()


class SchedulingInteractions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.get_cog("Database")

    async def owned_events_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        owned = await self.db.get_by_user(interaction.guild_id, interaction.user.id)
        return [ app_commands.Choice(name=item, value=item) for item in owned ]


    @app_commands.command(name="check", description="helper function to check if database is currently available")
    async def check(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.db.get_by_user(interaction.guild_id, interaction.user.id)
        await interaction.followup.send("Done!", ephemeral=True)


    @app_commands.command(name="assign",
                          description="Assigns a discord channel to which the bot will publish scheduled events")
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
                interaction.client.dispatch("update_calendar", interaction)


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
    @app_commands.autocomplete(name=owned_events_autocomplete)
    async def create(self, interaction: discord.Interaction, name:str, dates:str, starts:int=19, duration:int=4, color: app_commands.Choice[str]=None, mode:int=1, desc:str=""):
        """Shows the settings view."""
        await interaction.response.defer(ephemeral=True)

        chosen = color.value if color else discord.Color.random().__str__()
        try:
            event = Event(
                owner=interaction.user.id,
                name=name,
                description=desc,
                colour=chosen,
                mode=str(mode),
                dates=dates,
                starts=starts,
                duration=duration
            )
            view = EventSettings(event)
            await interaction.followup.send(view=view, ephemeral=True)
        except TypeError:
            await interaction.followup.send(content="User didnt enter a number in one of the dates", ephemeral=True)
        except ValueError:
            await interaction.followup.send(content="User didnt enter a valid date amongst the provided ones", ephemeral=True)


async def setup(bot):
    await bot.add_cog(SchedulingInteractions(bot))
