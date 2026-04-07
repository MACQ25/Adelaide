from __future__ import annotations

import enum
import random

import discord
from discord import app_commands


class EventColor(enum.Enum):
    red      = discord.Color.red()
    blue     = discord.Color.blue()
    green    = discord.Color.green()
    orange   = discord.Color.orange()
    purple   = discord.Color.purple()
    yellow   = discord.Color.yellow()
    white    = discord.Color.light_theme()
    black    = discord.Color.dark_theme()
    custom   = f'#{hex(random.randrange(0, 2**24))[2:]}'

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
            'custom': '🎨'
        }
        return emojis[self.name]

    def as_choice(self) -> app_commands.Choice:
        return app_commands.Choice(name=f"{self.emoji} {self.name.capitalize()}", value=str(self.value))

    def as_option(self) -> discord.SelectOption:
        return discord.SelectOption(label=self.name.capitalize(), emoji=self.emoji, value=str(self.value))
