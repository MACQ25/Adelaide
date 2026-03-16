import discord
from aiohttp.log import client_logger
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

description = 'This is a description'

bot = commands.Bot(command_prefix='/', description=description, intents=intents)

@bot.event
async def on_ready():
    # Tell the type checker that User is filled up at this point
    assert bot.user is not None

    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('--- God Save The Queen! ---')

@bot.command()
async def hi(ctx):
    await ctx.send("Henlo!")

tkn = open("secrets/token.tkn").readline().strip()

bot.run(tkn)