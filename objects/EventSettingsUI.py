from __future__ import annotations

from typing import Callable, Optional, Any
from discord._types import ClientT
from objects.Event import Event
import discord
from discord.ext.commands import Bot
from discord import ui, Interaction
from objects.EventColorEnum import EventColor
import datetime as dt


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

    def __init__(self, view: 'EventSettings', button: SetCustomButton):
        super().__init__()
        self.view = view
        self.values = view.data
        self.button = button

        self.textHelper = ui.TextDisplay(content="Color values formated in Hex format, for example #ff0000 for red, you may use an external color picker such as [this](https://www.figma.com/es-la/circulo-cromatico/)")

        self.colorInput1 = ui.TextInput(
            label="Enter the main color",
            style=discord.TextStyle.short,
            required=True,
            default=  view.data.custom_set_1 or view.data.color[0] or EventColor.custom.as_text(),
        )
        self.colorInput2 = ui.TextInput(
            label="secondary color for gradient, if any",
            style=discord.TextStyle.short,
            placeholder= EventColor.custom.as_text()
        )
        self.colorInput3 = ui.TextInput(
            label="Gradient degree (1.0 - 0.01, ideal 0.35)",
            style=discord.TextStyle.short,
            placeholder="1.0"
        )

        self.add_item(self.textHelper)
        self.add_item(self.colorInput1)
        self.add_item(self.colorInput2)
        self.add_item(self.colorInput3)



    async def on_submit(self, interaction: discord.Interaction[Bot]) -> None:
        try:
            self.values.custom_modified = True
            self.values.custom_set_1 = str(self.colorInput1.value)
            self.values.custom_set_2 = str(self.colorInput2.value) or str(self.colorInput1.value)
            self.values.custom_gradient = float(self.colorInput3.value) if (self.colorInput3.value.isnumeric() and float(self.colorInput3.value) <= 1.0) else 0.2
            self.values.color = [str(self.colorInput1.value)]
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
            option.default = option.value == self.values.color[0]


    def sync_custom_state(self):
        """Called after the modal submits — updates the Custom option label to show the set color."""
        for option in self.select_color.options:
            if option.label.__contains__("Custom"):
                option.value = self.values.custom_set_1
                option.label = f"Custom ({self.values.custom_set_1})"
                break
        self.update_options()


    @ui.select(placeholder='Select a color', options=[color.as_option() for color in EventColor])
    async def select_color(self, interaction: discord.Interaction[Bot], select: discord.ui.Select) -> None:
        if select.values[0].__contains__("Custom"):
            self.values.color = [self.values.custom_set_1]  # keep the last entered hex
        else:
            self.values.custom_modified = False
            self.values.color = [select.values[0]]
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
            option.default = option.value == str(self.values.frequency)

    @ui.select(
        placeholder='Select the frequency',
        options=[
            discord.SelectOption(label="Picked", description="the event will occur on a given set of days", value=str(1)),
            discord.SelectOption(label="Weekly", description="the event will occur every week at a given hour", value=str(2)),
            discord.SelectOption(label="Monthly", description="the event will occur every month at a given hour", value=str(3))
        ]
    )
    async def select_mode(self, interaction: discord.Interaction[Bot], select: discord.ui.Select) -> None:
        self.values.frequency = int(select.values[0])
        self.update_frequency()

        await interaction.response.edit_message(view=self.view)


class DatesModal(ui.Modal, title="Modal Title"):


    def __init__(self, view: 'EventSettings', button: SetDatesButton):
        super().__init__()
        self.view = view
        self.values = view.data
        self.button = button

        if self.view.malformed_dates:
            self.correction_display = ui.TextDisplay(f"Errors were found, following dates were invalid:\n {"\n".join(self.view.malformed_dates)} \n Errors will be deleted upon submission")
            self.add_item(self.correction_display)

        self.datesInput = ui.TextInput(
            label="dates",
            default=",\n".join([d.strftime("%Y-%m-%d %H:%M:%S%z") for d in  self.values.dates]),
            style=discord.TextStyle.paragraph,
            required=True,
        )

        self.add_item(self.datesInput)

    async def on_submit(self, interaction: discord.Interaction[Bot]) -> None:
        try:
            self.view.malformed_dates.clear()
            upd_dates = []
            for d in self.datesInput.value.split(","):
                try:
                    n_date = dt.datetime.strptime(d.strip(),"%Y-%m-%d %H:%M:%S%z")
                    upd_dates.append(n_date)
                except ValueError:
                    self.view.malformed_dates.append(d)

            self.values.dates = upd_dates
            self.view.finish_button.disabled = not self.view.is_valid

            self.view.build()
            await interaction.response.edit_message(view=self.view)
        except ValueError:
            await interaction.response.send_message('I am a error message and dumb and stupid.', ephemeral=True)



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


class AdvCreationModal(ui.Modal, title="New Zone for "):
    def __init__(self, view: 'EventSettings'):
        super().__init__()
        self.view = view
        self.values = view.data
        self.title = f'{self.title}{self.values.summary if len(self.values.summary) < 33 else f"{self.values.summary[:29]}..."}' if self.values.summary is not None else "The event is still unnamed tho..."

        self.sectionInput = ui.TextInput(
            label="Name of the new section",
            default=f'{self.values.summary}',
            style=discord.TextStyle.paragraph,
            required=True
        )

        self.channelInput = ui.TextInput(
            label="Name of the new text channel",
            default=f'{self.values.summary} general',
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.vcInput = ui.TextInput(
            label="Name of the new voice channel",
            default=f'{self.values.summary} vc',
            style=discord.TextStyle.paragraph,
            required=True
        )

        self.add_item(self.sectionInput)
        self.add_item(self.channelInput)
        self.add_item(self.vcInput)


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

    def __init__(self, owner, data: Event, full_featured=False, cc=False):
        super().__init__()

        self.data = data
        self.interaction_owner = owner
        self.full_featured = full_featured
        self.channel_flag = cc

        self.event_name_btn = SetTextButton(self.data, "summary", "Set Title", "Set a new title", self.data.summary)
        self.event_desc_btn = SetTextButton(self.data, "description", "Desc", "Write a description for the event", self.data.description)
        self.event_dates_btn = SetDatesButton(self.data)
        self.color_select = ColorSetting(self.data)
        self.custom_color_btn = SetCustomButton(self.data)

        if full_featured:
            self.count_button = SetCountButton(self.data)
            self.create_channel = ToggleButton("channel_flag", self.channel_flag, "Create 🛠️", "Use 🪧", self.build)
            self.configure_creation = AdvCreationButton(self.data)

        self.malformed_dates = []

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

        if self.full_featured:
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


        section_items = [
            ui.TextDisplay('## Date Information\n-# Days and hours in which the event will happen.'),
        ]

        if self.malformed_dates:
            section_items.append(
                ui.TextDisplay(f"Errors were found, following dates are invalid:\n {"\n".join(self.malformed_dates)}")
            )

        container.add_item(
            ui.Section(
                *section_items,
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

        if int(self.data.frequency) == 3:
            self.data.dates = [self.data.dates[0]]
        elif int(self.data.frequency) == 2:
            starting_from = self.data.dates[0]

            # Adding a +1 hoping no bugs to arise when it comes to February
            new_batch = list([starting_from])
            for x in range(5):
                n_date = starting_from + dt.timedelta(weeks=x + 1)
                if n_date.month == starting_from.month:
                    new_batch.append(n_date)

            self.data.dates = new_batch

        if self.data.custom_modified:
            self.data.color = [self.data.custom_set_1, self.data.custom_set_2, self.data.custom_gradient]

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
