from __future__ import annotations

from typing import Callable, Optional, Any

from discord._types import ClientT

from objects.Event import Event
import discord
from discord.ext.commands import Bot
from discord import ui, Interaction

from objects.EventColorEnum import EventColor


class TextModal(ui.Modal, title="Modal Title"):
    nameInput = ui.TextInput(style=discord.TextStyle.paragraph, required=True)

    def __init__(self, view: 'EventSettings', attribute: str, modal_title:str = "Set field", modal_label:str = "Value", modal_input:str = "New Value"):
        super().__init__()

        self.view = view
        self.values = view.data
        self.target_attribute = attribute

        self.title = modal_title
        self.nameInput.label = modal_label
        self.nameInput.default = modal_input


    async def on_submit(self, interaction: discord.Interaction[Bot]) -> None:
        try:
            setattr(self.values, self.target_attribute, self.nameInput.value)
            self.view.build()
            await interaction.response.edit_message(view=self.view)
        except ValueError:
            await interaction.response.send_message('Something Went Wrong.', ephemeral=True)


class SetTextButton(ui.Button['EventSettings']):
    def __init__(self, values: Event, attribute: str, modal_title:str = "Set field", modal_label:str = "Value", modal_input:str = "New Value"):
        super().__init__(
            label=modal_title,
            style=discord.ButtonStyle.secondary
        )
        self.values = values
        self.target_attribute = attribute
        self.modal_title = modal_title
        self.modal_label = modal_label
        self.modal_input = getattr(self.values, self.target_attribute) if not None else modal_input


    async def callback(self, interaction: discord.Interaction[Bot]) -> None:
        # Tell the type checker that a view is attached already
        assert self.view is not None
        await interaction.response.send_modal(TextModal(self.view, self.target_attribute, self.modal_title, self.modal_label, self.modal_input))


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
            self.view.color_select.sync_custom_state()

            self.view.finish_button.disabled = not self.view.is_valid
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

    def sync_custom_state(self):
        """Called after the modal submits — updates the Custom option label to show the set color."""
        for option in self.select_color.options:
            if option.label.__contains__("Custom"):
                option.value = self.values.custom_set
                option.label = f"Custom ({self.values.custom_set})"
                break
        self.update_options()


    @ui.select(placeholder='Select a color', options=[color.as_option() for color in EventColor])
    async def select_color(self, interaction: discord.Interaction[Bot], select: discord.ui.Select) -> None:
        if select.values[0].__contains__("Custom"):
            self.values.custom_modified = False
            self.values.color = self.values.custom_set  # keep the last entered hex
        else:
            self.values.custom_modified = False
            self.values.color = select.values[0]
        self.update_options()

        self.view.finish_button.disabled = not self.view.is_valid
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

            self.view.finish_button.disabled = not self.view.is_valid
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

            self.view.finish_button.disabled = not self.view.is_valid
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


class ToggleButton(ui.Button['EventSettings']):
    def __init__(self, attribute: str, value: bool, lbl1: str = "✅", lbl2: str = "❌", on_toggle: Optional[Callable] = None):
        super().__init__(
            label= lbl1 if value else lbl2,
            style=discord.ButtonStyle.secondary
        )
        self.target = attribute
        self.new_val = not value
        self.label1 = lbl1
        self.label2 = lbl2
        self.callback_flag = on_toggle is not None
        self.on_toggle = on_toggle

    async def callback(self, interaction: discord.Interaction[Bot]) -> None:
        assert self.view is not None
        self.view.__setattr__(self.target, self.new_val)
        self.new_val = not self.new_val
        self.label = self.label1 if not self.new_val else self.label2
        if self.callback_flag:
            self.on_toggle()
        await interaction.response.edit_message(view=self.view)


class ChannelSetting(ui.ActionRow['EventSettings']):
    def __init__(self, event: Event):
        super().__init__()
        self.data = event
        if event.channel is not None:
            self.select_channel.default_values = [
                discord.SelectDefaultValue(id=event.channel.id, type=discord.SelectDefaultValueType.channel)
            ]

    @ui.select(
        placeholder='Select a channel',
        channel_types=[discord.ChannelType.voice],
        max_values=1,
        min_values=0,
        cls=ui.ChannelSelect,
    )
    async def select_channel(self, interaction: discord.Interaction[Bot], select: ui.ChannelSelect) -> None:
        if select.values:
            channel = select.values[0]
            self.data.channel = interaction.client.get_partial_messageable(
                channel.id, guild_id=channel.guild_id, type=channel.type
            )
            select.default_values = [discord.SelectDefaultValue(id=channel.id, type=discord.SelectDefaultValueType.channel)]
        else:
            self.data.channel = None
            select.default_values = []

        self.view.finish_button.disabled = not self.view.is_valid
        await interaction.response.edit_message(view=self.view)


class MembersSetting(ui.ActionRow['EventSettings']):
    def __init__(self, event: Event):
        super().__init__()
        self.data = event
        self.update_options()

    def update_options(self):
        self.select_members.default_values = [
            discord.SelectDefaultValue(id=member.id, type=discord.SelectDefaultValueType.user)
            for member in self.data.members
        ]

    @ui.select(placeholder='Select members', min_values=0, max_values=12, cls=ui.UserSelect)
    async def select_members(self, interaction: discord.Interaction[Bot], select: ui.UserSelect) -> None:
        self.data.members = select.values
        self.data.owner_check(interaction.user)
        self.update_options()

        self.view.finish_button.disabled = not self.view.is_valid
        await interaction.response.edit_message(view=self.view)


class AdvCreationModal(ui.Modal, title="Create a Specific Zone for "):
    sectionInput = ui.TextInput(label="Name of the new section", default="", style=discord.TextStyle.paragraph, required=True)
    channelInput = ui.TextInput(label="Name of the new text channel", default="", style=discord.TextStyle.paragraph, required=True)
    vcInput = ui.TextInput(label="Name of the new voice channel", default="", style=discord.TextStyle.paragraph, required=True)

    def __init__(self, view: 'EventSettings'):
        super().__init__()
        self.view = view
        self.values = view.data

        if self.values.summary is not None:
            self.title = f'{self.title} {self.values.summary}'
            self.sectionInput.default = f'{self.values.summary}'
            self.channelInput.default = f'{self.values.summary} general'
            self.vcInput.default = f'{self.values.summary} vc'
        else:
            self.title = f'{self.title} your new Event'


    async def on_submit(self, interaction: discord.Interaction[Bot]) -> None:
        try:
            self.view.data.section = self.sectionInput.value
            self.view.data.text_channel = self.channelInput.value
            self.view.data.voice_channel = self.vcInput.value

            self.view.finish_button.disabled = not self.view.is_valid
            await interaction.response.edit_message(view=self.view)
        except ValueError:
            await interaction.response.send_message('Something Went Wrong.', ephemeral=True)


class AdvCreationButton(ui.Button['EventSettings']):
    def __init__(self, values: Event):
        super().__init__( label="⚙", style=discord.ButtonStyle.secondary )

    async def callback(self, interaction: discord.Interaction[Bot]) -> None:
        # Tell the type checker that a view is attached already
        assert self.view is not None
        await interaction.response.send_modal(AdvCreationModal(self.view))


class EventSettings(ui.LayoutView):

    @property
    def is_valid(self) -> bool:
        channel_valid = (self.data.channel or (
                self.data.section and (self.data.text_channel or self.data.voice_channel)
        ))

        return all([
            self.data.summary,
            self.data.color,
            self.data.frequency,
            len(self.data.dates) > 0,
            str(self.data.duration).isnumeric(),
            self.data.duration,
            (channel_valid if self.full_featured else True),
            ])

    row = ui.ActionRow()

    def __init__(self, owner, data: Event, full_featured=False):
        super().__init__()

        self.data = data
        self.interaction_owner = owner
        self.channel_flag = False
        self.full_featured = full_featured

        self.event_name_btn = SetTextButton(self.data, "summary", "Set Title", "Set a new title", self.data.summary)
        self.event_desc_btn = SetTextButton(self.data, "description", "Desc", "Write a description for the event", self.data.description)
        self.event_dates_btn = SetDatesButton(self.data)
        self.color_select = ColorSetting(self.data)
        self.custom_color_btn = SetCustomButton(self.data)

        if full_featured:
            self.count_button = SetCountButton(self.data)
            self.create_channel = ToggleButton("channel_flag", self.channel_flag, "Create 🛠️", "Use 🪧", self.build)
            self.configure_creation = AdvCreationButton(self.data)

        self.build()


    def build(self):
        # For this example, we'll use multiple sections to organize the settings.
        self.clear_items()

        container = ui.Container()
        header = ui.TextDisplay('# Settings\n-# This is an example to showcase how to do settings.')
        container.add_item(header)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))

        container.add_item(
            ui.Section(
                ui.TextDisplay(f'## Event Name\n-# The name to be saved to the discord UI. \n\nCurrent: { ("\n**"  + self.data.summary + "**") if self.data.summary else " You MUST set a title"}\n'),
                accessory=self.event_name_btn,
            )
        )

        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        container.add_item(
            ui.Section(
                ui.TextDisplay(f'## Description\n-# Extra details to be saved to UI. \n\nCurrent: { ("\n*"  + self.data.description + "*") if self.data.description else " No description yet"}'),
                accessory=self.event_desc_btn,
            )
        )


        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(
            ui.Section(
                ui.TextDisplay('## Color Selection\n-# This is the color that is shown in the calendar image.'),
                accessory=self.custom_color_btn
            )

        )
        container.add_item(self.color_select)


        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(
            ui.Section(
                ui.TextDisplay('## Date Information\n-# Days and hours in which the event will happen.'),
                accessory=self.event_dates_btn
            )
        )
        container.add_item(FrequencySelect(self.data))


        if self.full_featured:
            container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))

            container.add_item(
                ui.Section(
                    ui.TextDisplay('### Event Duration\n-# This is the number of hours the event will last (only reflected in discord UI).'),
                    accessory=self.count_button,
                )
            )

            container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

            container.add_item(
                ui.Section(
                    ui.TextDisplay('### Create Channel or Use Pre-existing?'),
                    accessory=self.create_channel,
                )
            )

            container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

            if self.channel_flag:
                #self.data.toggle_channel_feature(False)
                container.add_item(
                    ui.Section(
                        ui.TextDisplay('### Configure New Section and Channel\'s information'),
                        accessory=self.configure_creation,
                    )
                )
            else:
                #self.data.toggle_channel_feature(True)
                container.add_item(ui.TextDisplay('### Channel Selection\n-# This is the channel where the message will be sent.'))
                container.add_item(ChannelSetting(self.data))

            container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

            self.data.owner_check(self.interaction_owner)
            container.add_item(
                    ui.TextDisplay('### Member Selection\n-# These are the members that will be mentioned in the message.')
                )
            container.add_item(MembersSetting(self.data))


        self.add_item(container)

        # Swap the row so it's at the end
        self.remove_item(self.row)
        self.remove_item(self.row)
        self.add_item(self.row)
        self.finish_button.disabled = not self.is_valid


    @row.button(label='Finish', style=discord.ButtonStyle.green)
    async def finish_button(self, interaction: discord.Interaction[Bot], button: ui.Button) -> None:
        # Edit the message to make it the interaction response...
        await interaction.response.edit_message(view=self)
        # ...and then send a confirmation message.
        await interaction.followup.send(f'Settings saved.', ephemeral=True)

        # Then delete the settings panel
        self.stop()

        if self.data.custom_modified:
            self.data.color = self.data.custom_set

        self.data.owner_check(interaction.user)

        if self.full_featured:
            self.data.created_for_event = self.channel_flag
            if self.channel_flag:
                interaction.client.dispatch("event_channel_creation", interaction, self.data)
            else:
                interaction.client.dispatch("event_full_creation_scheduling", interaction, self.data)
        else:
            interaction.client.dispatch("ext_event_creation", interaction, self.data)

        await interaction.delete_original_response()
