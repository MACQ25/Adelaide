import datetime as dt

import discord
from discord.app_commands import guilds
from discord.ext import commands
from discord.ext.commands import Context, Bot
from discord import app_commands, ui
from unicodedata import category

from objects.Event import Event


async def role_creation(interaction: discord.Interaction, event: Event):
    guild = interaction.guild

    e_role: discord.Role = discord.utils.get(guild.roles, name=event.summary)

    if e_role is not None:
        if e_role.permissions.administrator:
            raise Exception("User tried getting away with stealing a role for this event, for shame!")
        else:
            await interaction.user.add_roles(e_role, reason="Creator of event")
            return e_role.id
    else:
        n_role = await guild.create_role(
            name=event.summary,
            color=discord.Color.from_str(event.custom_set if event.custom_modified else event.color),
            mentionable=True,
            hoist=False,
            reason=f"Created for event: {event.summary} by {interaction.user.name}"
        )
        await interaction.user.add_roles(n_role, reason="Creator of event")
        return n_role.id


async def role_deletion(interaction: discord.Interaction, role_id: int):
    guild = interaction.guild
    await guild.get_role(role_id).delete(reason="Event type is being deleted")


class InternalEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_event_channel_creation(self, interaction: discord.Interaction, event: Event):
        section = None
        guild = interaction.guild
        f_category = discord.utils.get(interaction.guild.categories, name=event.section)
        if f_category is None:
            section = await guild.create_category(event.section)
            text_channel = await guild.create_text_channel(event.text_channel, category=section)
            voice_channel = await guild.create_voice_channel(event.voice_channel, category=section)
        else:
            text_channel = await guild.create_text_channel(event.text_channel, category=f_category)
            voice_channel = await guild.create_voice_channel(event.voice_channel, category=f_category)

        event.section = f_category.id if f_category else section.id
        event.text_channel = text_channel.id
        event.voice_channel = voice_channel.id

        interaction.client.dispatch("event_full_creation_scheduling", interaction, event)


    @commands.Cog.listener()
    async def on_event_full_creation_scheduling(self, interaction: discord.Interaction, event: Event):
        try:
            guild = interaction.guild
            c_channel = guild.get_channel(event.voice_channel)

            for date in event.dates:
                date_obj = dt.datetime.strptime(date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc)

                s_event = await guild.create_scheduled_event(
                    name=event.summary,
                    description=event.description,
                    start_time=date_obj,
                    end_time=date_obj + dt.timedelta(hours=int(event.duration)),
                    entity_type=discord.EntityType.voice,
                    channel=c_channel,
                    privacy_level=discord.PrivacyLevel.guild_only,
                )
                s_event._add_user(interaction.user)

                event.int_evt.append(s_event.id)

            event.role = await role_creation(interaction, event)
            interaction.client.dispatch("ext_event_creation", interaction, event)

        except Exception as e:
            print(f"Listener error: {e!r}")


    @commands.Cog.listener()
    async def on_notify_invitations(self, interaction: discord.Interaction, role_id: int, channel_id: int, mentions: list):
        guild = interaction.guild
        assert all(isinstance(m, discord.Member) for m in mentions)
        cleaned_mentions = (", ".join(f"<@{user.id}>" for user in mentions if user.id is not interaction.user.id))
        await guild.get_channel(channel_id).send(content=f"Welcome! this is the official channel of <@&{role_id}>\n <@{interaction.user.id}> has invited you to join\n" + cleaned_mentions)


    @commands.Cog.listener()
    async def on_quick_creation(self, event_name:str, dates:list, starts:int, duration:int):
        pass


    @commands.Cog.listener()
    async def on_remove_channels(self, interaction: discord.Interaction, event_data: dict):
        guild = interaction.guild

        for channel_id in (event_data.get("vc_id"), event_data.get("text_id")):
            l_channel = guild.get_channel(channel_id)
            if l_channel:
                await l_channel.delete()

        l_category = guild.get_channel(event_data.get("section_id"))
        if l_category:
            await l_category.delete()


    @commands.Cog.listener()
    async def on_remove_scheduled(self, interaction: discord.Interaction, scheduled_list: list):
        guild = interaction.guild
        for se in scheduled_list:
            await guild.get_scheduled_event(se).delete()


async def setup(bot: commands.Bot):
    await bot.add_cog(InternalEvents(bot))