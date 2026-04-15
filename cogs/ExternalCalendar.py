import calendar
from datetime import datetime as dt
import discord
from discord.ext import commands
from discord import app_commands, ui, Button
from discord.ui import View
from objects.Event import Event
from CalendarImageGen import draw
from cogs.InternalEvents import role_deletion


class ExternalCalendar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.get_cog("Database")


    @commands.Cog.listener()
    async def on_update_calendar(self, interaction: discord.Interaction):
        data =  await self.db.get_events(interaction.guild_id)

        current_day = dt.today()
        event_labels = [list() for _ in range(calendar.monthrange(current_day.year, current_day.month)[1])]

        colors = {e["name"]: e["color"] for e in data.get("event_data", [])}
        #roles = [r.get('role_id') for r in data.get("event_data", []) if 'role_id' in r]

        for pair in data.get("event_days").items():
            if pair[0] not in colors:
                continue
            for ev in pair[1]:
                event_labels[dt.fromisoformat(ev.get('date').split()[0]).day - 1].append([pair[0], colors[pair[0]]])

        img = await draw(guild_id=interaction.guild_id, events=event_labels)

        assigned_id = data.get("assigned_channel")
        if assigned_id != 'n/a':
            for ch in interaction.guild.text_channels:
                try:
                    ch_pins = await ch.pins()
                    for msg in ch_pins:
                        if msg.author.id == interaction.client.user.id:
                            await msg.unpin()
                            await msg.delete()

                    async for msg in ch.history(limit=100):
                        if msg.type == discord.MessageType.pins_add and msg.author.id == interaction.client.user.id:
                            await msg.delete()
                except discord.Forbidden:
                    continue  # skip channels the bot can't access
                except discord.NotFound:
                    continue

            channel = await interaction.client.fetch_channel(assigned_id.get('channel_id'))

            file = discord.File(img, filename="Calendar.jpeg")
            embed = discord.Embed(title=f"📅 {dt.now().strftime("%B")} Calendar", color=discord.Color.blue())
            embed.set_image(url="attachment://Calendar.jpeg")
            embed.description = "Scheduled Events: " + ", ".join(f"<@&{r.get('role_id')}>" for r in data.get("event_data", []) if 'role_id' in r)
            embed.set_footer(text=f"Last updated: {dt.today().strftime('%Y-%m-%d %H:%M')}")

            msg = await channel.send(embed=embed, file=file)
            await msg.pin()

            await interaction.followup.send("updated on assigned channel!", ephemeral=True)
        else:
            await interaction.followup.send(file=discord.File(img, "Calendar.jpeg"), ephemeral=True)


    @commands.Cog.listener()
    async def on_ext_event_creation(self, interaction: discord.Interaction, event: Event):
        try:
            # role = await guild.create_role(name=event.summary, color=discord.Color.from_str(event.color))

            if int(event.frequency) == 3:
                event.dates = [event.dates[0]]
            elif int(event.frequency) == 2:
                starting_from = dt.fromisoformat(event.dates[0])
                c_month = calendar.monthrange(starting_from.year, starting_from.month)
                new_batch = list()
                # Adding a +1 hoping no bugs to arise when it comes to February
                for x in range(starting_from.day, c_month[1] + 1, 7):
                    new_batch.append(starting_from.replace(day=x).__str__())
                event.dates = new_batch
            await self.db.save_event(interaction.guild_id, event)
        except Exception as e:
            print("exception found on listener")
        finally:
            interaction.client.dispatch("update_calendar", interaction)
            if event.role is not None:
                interaction.client.dispatch(
                    "notify_invitations",
                    interaction,
                    event.role,
                    event.text_channel if event.created_for_event else event.voice_channel,
                    event.members
                )


    @commands.Cog.listener()
    async def on_ext_event_q_creation(self, interaction: discord.Interaction, event_name:str, dates:list, starts:int, duration:int):
        success: bool
        success = await self.db.quick_create(interaction.guild_id, interaction.user.id, event_name, dates, starts, duration)
        if success:
            interaction.client.dispatch("update_calendar", interaction)
        else:
            await interaction.followup.send("Something went wrong while processing this request")


    @commands.Cog.listener()
    async def on_ext_event_cancellation(self, interaction: discord.Interaction, event_name:str, targets:list, all_flag:bool):
        success: bool
        if all_flag:
            success = await self.db.delete_by_class(interaction.guild_id, interaction.user.id, event_name)
        else:
            success = await self.db.delete_set(interaction.guild_id, interaction.user.id, event_name, targets)

        if success:
            interaction.client.dispatch("update_calendar", interaction)
        else:
            await interaction.followup.send("Something went wrong while processing this request")


    @commands.Cog.listener()
    async def on_ext_event_hiatus(self, interaction: discord.Interaction, event_name:str, to_fro:bool):
        success = await self.db.update_to_inactive(interaction.guild_id, interaction.user.id, event_name, to_fro)
        if success:
            interaction.client.dispatch("update_calendar", interaction)
        else:
            await interaction.followup.send("Something went wrong while processing this request")


    @commands.Cog.listener()
    async def on_ext_event_full_clean(self, interaction: discord.Interaction, event_name:str):
        int_data = await self.db.get_internal(interaction.guild_id, interaction.user.id, event_name)
        event_data = int_data.get("event_data")

        interaction.client.dispatch("remove_scheduled", interaction, int_data.get("event_days"))
        await role_deletion(interaction, event_data.get("role_id"))

        if event_data.get("event_owns_it"):
            interaction.client.dispatch("remove_channels", interaction, event_data)

        ext_success = await self.db.delete_full(interaction.guild_id, interaction.user.id, event_name)
        if ext_success:
            interaction.client.dispatch("update_calendar", interaction)
        else:
            await interaction.followup.send("Something went wrong while processing this request")


    @app_commands.command(name="force-refresh", description="Forces a refresh of the pinned calendar")
    async def fr(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        interaction.client.dispatch("update_calendar", interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(ExternalCalendar(bot))