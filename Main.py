import datetime as dt
from typing import Callable, Optional

import discord
from aiohttp.log import client_logger
from discord.ext import commands
import os
import asyncio
import calendar

from discord.ext.commands import Context

intents = discord.Intents.all()
intents.members = True
intents.message_content = True

description = 'This is a description'

bot = commands.Bot(command_prefix=commands.when_mentioned_or('/'), description=description, intents=intents)

@bot.event
async def on_ready():
    # Tell the type checker that User is filled up at this point
    assert bot.user is not None
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('--- God Save The Queen! ---')

    db_access = bot.get_cog("Database")
    bot_reg = [g async for g in bot.fetch_guilds()]

    if db_access is not None:
        await db_access.check_guilds(bot_reg)
        bot.loop.create_task(perform_cleanup(db_access.clean_old))


@bot.event
async def on_guild_join(guild):
    db_access = bot.get_cog("Database")
    if db_access is not None:
        await db_access.check_guilds([guild])


@bot.event
async def on_error(event, *args, **kwargs):
    print(f"Error in {event}:", args, **kwargs)
    raise


@bot.command()
@commands.is_owner()
async def sync(ctx: Context):
    msg = await ctx.reply("syncing...", silent=True)
    bot.tree.copy_global_to(guild=discord.Object(id=ctx.guild.id))
    await bot.tree.sync(guild=discord.Object(id=ctx.guild.id))
    await msg.edit(content="Synced!")


async def issue_updates():
    db = bot.get_cog("Database")
    to_update = await db.get_all_with_assigned() if db is not None else []
    update_cog = bot.get_cog("ExternalCalendar")

    for _id in to_update:
        await update_cog.update_calendar(_id)


async def perform_cleanup(cleanup_func: Optional[Callable] = None):
    while True:
        c_time = dt.datetime.today()
        month_len = calendar.monthrange(c_time.year, c_time.month)
        time_to_next = ((month_len[1] - c_time.day) * 86400) + (86400 - ((((c_time.hour * 60) + c_time.minute) * 60) + c_time.second))
        print(c_time)
        print(f"{time_to_next} seconds til next execution")
        await asyncio.sleep(time_to_next)
        if cleanup_func is not None:
            await cleanup_func()
            asyncio.create_task(issue_updates())


tkn = open("secrets/token.tkn").readline().strip()


async def load():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")


async def main():
    async with bot:
        await load()
        await bot.start(tkn)


asyncio.run(main())

#bot.run(tkn)