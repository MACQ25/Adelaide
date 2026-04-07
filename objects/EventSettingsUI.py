from __future__ import annotations

from objects.Event import Event
import discord
from discord.ext.commands import Bot
from discord import ui

from objects.EventColorEnum import EventColor


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


class CustomizeModal(ui.Modal, title="Set Custom Color"):
    colorInput = ui.TextInput(label="Enter a color in hex format", style=discord.TextStyle.paragraph, required=True)

    def __init__(self, view: 'EventSettings', button: SetCustomButton):
        super().__init__()
        self.view = view
        self.values = view.data
        self.button = button
        self.colorInput.default = view.data.color if self.values.custom_modified else view.data.custom_set

    async def on_submit(self, interaction: discord.Interaction[Bot]) -> None:
        try:
            self.values.custom_modified = True
            self.values.custom_set = str(self.colorInput.value)
            self.values.color = str(self.colorInput.value)
            await interaction.response.edit_message(view=self.view)
        except ValueError:
            await interaction.response.send_message('Something Went Wrong.', ephemeral=True)


class SetCustomButton(ui.Button['EventSettings']):
    def __init__(self, values: Event):
        super().__init__(label="🎨", style=discord.ButtonStyle.secondary)
        self.values = values

    async def callback(self, interaction: discord.Interaction[Bot]) -> None:
        # Tell the type checker that a view is attached already
        assert self.view is not None
        await interaction.response.send_modal(CustomizeModal(self.view, self))


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

        self.custom_color_btn = SetCustomButton(self.data)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(
            ui.Section(
                ui.TextDisplay('## Color Selection\n-# This is the color that is shown in the calendar image.'),
                accessory=self.custom_color_btn
            )

        )
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

        if self.data.custom_modified:
            self.data.color = self.data.custom_set

        # Then delete the settings panel
        self.stop()
        interaction.client.dispatch("ext_event_creation", interaction, self.data)

        await interaction.delete_original_response()