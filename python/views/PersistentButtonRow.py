from typing import Any
import discord
from discord import Interaction
from discord._types import ClientT
from discord.ext import commands

from python.views.EventColorEnum import EventColor


def get_event_color(color: discord.Color) -> EventColor:
    return next(
        (e for e in EventColor if isinstance(e.value, discord.Color) and e.value.value == color.value),
        None
    )

class RoleDropdown(discord.ui.Select):
    def __init__(self, options: list):

        self.value = -1
        super().__init__(placeholder='Select One', min_values=1, max_values=1, options=options)


    def update_options(self):
        for option in self.options:
            option.default = option.value == self.value


    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        self.value = self.values[0]
        self.update_options()
        await interaction.response.edit_message(view=self.view)


class DropdownView(discord.ui.View):

    def __init__(self, options: list):
        super().__init__()
        self.drp = RoleDropdown(options)
        self.add_item(self.drp)

    @discord.ui.button(label='Finish', style=discord.ButtonStyle.green, row=4)
    async def finish_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:

        to_assign = interaction.guild.get_role(int(self.drp.values[0]))

        if to_assign:
            await interaction.user.add_roles(to_assign, reason="Self assigned via funny bot")

        await interaction.response.edit_message(content="Assignment done", view=None)


class PersistentButtonRow(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)


    @discord.ui.button(
        label="Join One",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_button:assign_role"
    )
    async def assign_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild
        db = interaction.client.get_cog("Database")
        data =  await db.get_events(guild.id)

        options = []
        for ent in data.get("event_data"):
            if "role_id" not in ent:
                continue
            r = guild.get_role(ent.get("role_id"))  # resolve int -> Role
            if r is None:
                continue
            ec = get_event_color(r.color)
            options.append(discord.SelectOption(label=r.name, value=str(r.id), emoji=ec.emoji if ec else '👤'))

        if options:
            view = DropdownView(options=options)
            await interaction.response.send_message("Choose one", view=view, ephemeral=True)
        else:
            await interaction.response.send_message("No events with an associated role, sorry :p", ephemeral=True)

