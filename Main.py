import discord
from aiohttp.log import client_logger
from discord.ext import commands
import os
import asyncio

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


@bot.event
async def on_guild_join(guild):
    db_access = bot.get_cog("Database")
    if db_access is not None:
        await db_access.check_guilds(list(guild))


@bot.command()
async def hi(ctx):
    await ctx.send("Henlo!")

@bot.command()
@commands.is_owner()
async def sync(ctx: Context):
    msg = await ctx.reply("syncing...", silent=True)
    bot.tree.copy_global_to(guild=discord.Object(id=ctx.guild.id))
    await bot.tree.sync(guild=discord.Object(id=ctx.guild.id))
    await msg.edit(content="Synced!")


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