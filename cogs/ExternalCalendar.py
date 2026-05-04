import calendar
from datetime import datetime as dt, tzinfo, datetime
from datetime import date, timedelta
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands
from discord import app_commands
from cogs.SchedulingInteractions import defer
from objects.AutocompleteMixin import AutocompleteMixin
from objects.Event import Event
from CalendarImageGen import draw
from cogs.InternalEvents import role_deletion, scheduled_events


async def check_permissions_assigned(bot, channel: discord.TextChannel) -> dict:
    p = channel.permissions_for(channel.guild.get_member(bot.user.id))

    perms_checked = {
        "View Channel": p.view_channel,
        "Read Message History": p.read_message_history,
        "Send Messages": p.send_messages,
        "Pin Messages": p.pin_messages,
        "Manage Messages": p.manage_messages,
        "Attach Files": p.attach_files
    }

    return perms_checked


def lacks_perms_msg(bot, channel, permission_dict):
    return f"Could not set up channel, missing permissions for <@{bot.user.id}> on <#{channel.id}>\n\n**MISSING**:\n" + "\n".join([k for k in permission_dict.keys() if not permission_dict[k]])


class ExternalCalendar(AutocompleteMixin, commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.get_cog("Database")
        self.setup_db(self.bot)


    async def update_calendar(self, guild_id: int, interaction:discord.Interaction = None):
        data =  await self.db.get_events(guild_id)

        tmz = data.get("timezone", {}).get("tz_name", "UTC")
        upd_time = dt.today().astimezone(ZoneInfo(tmz))
        event_labels = [list() for _ in range(calendar.monthrange(upd_time.year, upd_time.month)[1])]

        colors = {e["name"]: e["color"] for e in data.get("event_data", [])}

        for pair in data.get("event_days").items():
            if pair[0] not in colors:
                continue
            for ev in pair[1]:
                #dt.fromisoformat(ev.get('date').split()[0]).day - 1
                l_date: datetime = ev.get('date')
                event_labels[l_date.day - 1].append([pair[0], colors[pair[0]]])

        img = await draw(guild_id=guild_id, events=event_labels)

        assigned_id = data.get("assigned_channel")
        if assigned_id != 'n/a':

            bot_id = self.bot.user.id
            a_channel = await self.bot.fetch_channel(assigned_id.get('channel_id'))
            perms = await check_permissions_assigned(self.bot, a_channel)

            if all(perms.values()):
                guild: discord.Guild = self.bot.get_guild(guild_id)

                if guild is None:
                    return

                channels = await guild.fetch_channels()
                for ch in channels:
                    if not isinstance(ch, discord.TextChannel):
                        continue
                    try:
                        ch_pins = await ch.pins()
                        for msg in ch_pins:
                            if msg.author.id == bot_id:
                                await msg.unpin()
                                await msg.delete()

                        async for msg in ch.history(limit=100):
                            if msg.author.id == bot_id and (msg.type == discord.MessageType.pins_add or msg.embeds):
                                await msg.delete()
                    except discord.Forbidden:
                        continue  # skip channels the bot can't access
                    except discord.NotFound:
                        continue


                file = discord.File(img, filename="Calendar.jpeg")
                embed = discord.Embed(title=f"📅 {upd_time.strftime("%B")} Calendar", color=discord.Color.blue())
                embed.set_image(url="attachment://Calendar.jpeg")
                embed.description = "Scheduled Events: " + ", ".join(f"<@&{r.get('role_id')}>" for r in data.get("event_data", []) if 'role_id' in r)
                embed.set_footer(text=f"Last updated: {upd_time.strftime('%Y-%m-%d %H:%M')}, {tmz}")

                msg = await a_channel.send(embed=embed, file=file)
                await msg.pin()

                if interaction is not None:
                    await interaction.followup.send("updated on assigned channel!", ephemeral=True)
            else:
                if interaction is not None:
                    await interaction.followup.send(content=lacks_perms_msg(self.bot, a_channel, perms), file=discord.File(img, "Calendar.jpeg"), ephemeral=True)
        else:
            if interaction is not None:
                await interaction.followup.send(file=discord.File(img, "Calendar.jpeg"), ephemeral=True)


    @commands.Cog.listener()
    async def on_ext_event_creation(self, interaction: discord.Interaction, event: Event):
        try:
            # role = await guild.create_role(name=event.summary, color=discord.Color.from_str(event.color))
            await self.db.save_event(interaction.guild_id, event)
        except Exception as e:
            print("exception found on listener")
        finally:
            await self.update_calendar(interaction.guild.id, interaction)
            if event.role is not None:
                interaction.client.dispatch(
                    "notify_invitations",
                    interaction,
                    event.role,
                    event.text_channel if event.created_for_event else event.channel.id,
                    event.members,
                    event.int_evt
                )


    @commands.Cog.listener()
    async def on_ext_event_q_creation(self, guild:discord.Guild|int, u_id:int, event_name:str, dates:list, starts:int, duration:int, int_events_id:list|None=None, interaction:discord.Interaction|None=None, admin:bool=False):
        success: bool

        if isinstance(guild, discord.Guild):
           guild = guild.id

        success = await self.db.quick_create(guild, u_id, event_name, dates, starts, duration, int_events_id, admin)
        if success and interaction is not None:
            await self.update_calendar(guild, interaction)
        else:
            await interaction.followup.send("Something went wrong while processing this request")


    @commands.Cog.listener()
    async def on_ext_event_cancellation(self, interaction: discord.Interaction, event_name:str, targets:list, all_flag:bool):
        success: bool
        internals = None

        if all_flag:
            internals = await self.db.get_all_internal_id(interaction.guild_id, interaction.user.id, event_name)
            success = await self.db.delete_by_class(interaction.guild_id, interaction.user.id, event_name)
        else:
            internals = await self.db.get_date_internals(interaction.guild_id, event_name, targets)
            success = await self.db.delete_set(interaction.guild_id, interaction.user.id, event_name, targets)

        if success:
            if internals and len(internals) > 0:
                interaction.client.dispatch("remove_scheduled", interaction, internals)
            await self.update_calendar(interaction.guild.id, interaction)
        else:
            await interaction.followup.send("Something went wrong while processing this request")


    @commands.Cog.listener()
    async def on_ext_event_hiatus(self, interaction: discord.Interaction, event_name:str, active:bool):
        success = await self.db.update_to_inactive(interaction.guild_id, interaction.user.id, event_name, active)
        if success:
            await self.update_calendar(interaction.guild.id, interaction)

            if not active:
                internals = await self.db.get_all_internal_id(interaction.guild_id, interaction.user.id, event_name)
                if internals and len(internals) > 0:
                    interaction.client.dispatch("remove_scheduled", interaction, internals)
                    await self.db.delete_internal_id(interaction.guild_id, interaction.user.id, event_name)
            else:
                scheduled: dict = await self.db.get_by_class(interaction.guild_id, event_name)
                event_data = await self.db.get_internal_data(interaction.guild_id, interaction.user.id, event_name)
                if event_data and event_data.get("vc_id"):

                    c_channel = interaction.guild.get_channel(event_data.get("vc_id"))
                    days = [d.get("date") for d in scheduled]
                    duration = [d.get("duration") for d in scheduled]

                    n_id = await scheduled_events(event_name, event_data.get("desc"), days, duration, interaction.guild, c_channel)

                    if len([r for r in n_id if r > 0]) > 0:
                        for ind, ev in enumerate(scheduled):
                            if n_id[ind] > 0:
                                ev["internal_id"] = n_id[ind]
                        await self.db.update_dates(interaction.guild_id, event_name, scheduled)
        else:
            await interaction.followup.send("The event is already inactive or you dont have the permissions to perform this action")


    @commands.Cog.listener()
    async def on_ext_event_full_clean(self, interaction: discord.Interaction, event_name:str):
        event_data = await self.db.get_internal_data(interaction.guild_id, interaction.user.id, event_name)
        date_id = await self.db.get_all_internal_id(interaction.guild_id, interaction.user.id, event_name)

        if date_id and len(date_id) > 0:
            interaction.client.dispatch("remove_scheduled", interaction, date_id)

        await role_deletion(interaction, event_data.get("role_id"))

        if event_data.get("event_owns_it"):
            interaction.client.dispatch("remove_channels", interaction, event_data)

        ext_success = await self.db.delete_full(interaction.guild_id, interaction.user.id, event_name)
        if ext_success:
            await self.update_calendar(interaction.guild.id, interaction)
        else:
            await interaction.followup.send("Something went wrong while processing this request")


    @app_commands.command(name="force-refresh", description="Forces a refresh of the pinned calendar")
    async def fr(self, interaction: discord.Interaction):
        # noinspection PyUnresolvedReferences
        await interaction.response.defer(ephemeral=True)
        await self.update_calendar(interaction.guild.id, interaction)


    @app_commands.command(name="server_timezone", description="Assigns a timezone to this server, used when constructing the calendar for technical purposes")
    @app_commands.autocomplete(timezone=AutocompleteMixin.timezone_autocomplete)
    async def tmz(self, interaction: discord.Interaction, timezone:str):
        await defer(interaction)
        upd = await self.db.update_timezone(interaction.guild_id, timezone)
        await interaction.followup.send(content=f"Update successful, updated to {timezone}" if upd else "Something went wrong, likely connection to the Database")


    @app_commands.command(name="assign",
                              description="Assigns a discord channel to which the bot will publish scheduled events")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def assign_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await defer(interaction)
        result_msg = ""
        send_update_out = False

        perms = await check_permissions_assigned(self.bot, channel)
        try:
            if all(perms.values()):
                await self.db.save_assigned(interaction.guild.id, channel)
                result_msg = "Channel updated to {}".format(channel)
                send_update_out = True
        except Exception:
            result_msg = "Could not update to target channel"
        finally:
            if not all(perms.values()):
                result_msg = lacks_perms_msg(self.bot, channel, perms)

            await interaction.followup.send(result_msg, ephemeral=True)

            if send_update_out:
                await self.bot.get_cog("ExternalCalendar").update_calendar(interaction.guild.id, interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(ExternalCalendar(bot))