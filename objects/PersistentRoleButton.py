from typing import Any
import discord
from discord import Interaction
from discord._types import ClientT
from discord.ext import commands
from objects.EventColorEnum import EventColor


def get_event_color(color: discord.Color) -> EventColor:
    return next(
        (e for e in EventColor if isinstance(e.value, discord.Color) and e.value.value == color.value),
        None
    )

class RoleDropdown(discord.ui.Select):
    def __init__(self, guild:discord.Guild, role_list:list[int]):

        self.value = -1

        options = []
        for r in role_list:
            r = guild.get_role(r)  # resolve int -> Role
            if r is None:
                continue
            ec = get_event_color(r.color)
            options.append(discord.SelectOption(label=r.name, value=str(r.id), emoji=ec.emoji if ec else '👤'))

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(placeholder='Select One', min_values=1, max_values=1, options=options)


    def update_options(self):
        for option in self.options:
            option.default = option.value == self.value


    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        self.value = self.values[0]
        self.update_options()
        await interaction.response.edit_message(view=self.view)


class DropdownView(discord.ui.View):

    def __init__(self, guild: discord.Guild, role_list: list[int]):
        super().__init__()
        self.drp = RoleDropdown(guild, role_list)
        self.add_item(self.drp)

    @discord.ui.button(label='Finish', style=discord.ButtonStyle.green, row=4)
    async def finish_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:

        to_assign = interaction.guild.get_role(int(self.drp.values[0]))

        if to_assign:
            await interaction.user.add_roles(to_assign, reason="Self assigned via funny bot")

        await interaction.response.edit_message(content="Assignment done", view=None)


class PersistentRoleButton(discord.ui.View):
    def __init__(self, role_list:list[int]=None):
        super().__init__(timeout=None)
        self.role_list = role_list

    @discord.ui.button(
        label="Join One",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_button:assign_role"
    )
    async def assign_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = DropdownView(guild=interaction.guild, role_list=self.role_list)
        await interaction.response.send_message("Choose one", view=view, ephemeral=True)