import datetime as dt
import uuid
import discord
from discord import app_commands
from discord.ext import commands
from utils.AutocompleteMixin import AutocompleteMixin
from data_entities.Event import Event
from utils.InteractionDefer import defer
from utils.RoleCheck import role_check
from utils.RuntimeConfig import ensure_directories


async def process_image(image: discord.Attachment, interaction: discord.Interaction) -> tuple[str, bytes]:
    if not image.content_type or not image.filename.lower().endswith(("png", "jpeg", "jpg")):
        await interaction.followup.send("Provided attachment was invalid")
        raise ValueError("Invalid image attachment")

    image_bytes = await image.read()
    file_name = f"{interaction.user.id}_{uuid.uuid4()}.{image.filename.split(".")[1]}"

    return file_name, image_bytes


async def save_thumbnail(file_name: str, image_bytes: bytes):
    ensure_directories("images/event_thumbnail")
    with open(f"images/event_thumbnail/{file_name}", "wb") as f:
        f.write(image_bytes)


async def role_creation(interaction: discord.Interaction, event: Event):
    guild = interaction.guild

    e_role: discord.Role = discord.utils.get(guild.roles, name=event.name)

    if e_role is not None:
        if e_role.permissions.administrator:
            raise Exception("User tried getting away with stealing a role for this event, for shame!")
        else:
            await interaction.user.add_roles(e_role, reason="Creator of event")
            return e_role.id
    else:
        n_role = await guild.create_role(
            name=event.name,
            color=discord.Color.from_str(event.custom_set_1 if event.custom_modified else event.color[0]),
            mentionable=True,
            hoist=False,
            reason=f"Created for event: {event.name} by {interaction.user.name}"
        )
        await interaction.user.add_roles(n_role, reason="Creator of event")
        return n_role.id


async def role_deletion(interaction: discord.Interaction, role_id: int):
    guild = interaction.guild
    await guild.get_role(role_id).delete(reason="Event type is being deleted")


async def scheduled_events(ev_data: Event, guild: discord.Guild, channel: discord.VoiceChannel):
    id_list = []

    img = None
    if ev_data.image:
        if isinstance(ev_data.image, str):
            with open(f"images/event_thumbnail/{ev_data.image}", "rb") as f:
                img = f.read()
        else:
            img = ev_data.image[1]

    now = dt.datetime.now().replace(tzinfo=ev_data.dates[0].tzinfo)

    for ind, date in enumerate(ev_data.dates):
        if date > now:

            end_time = date + dt.timedelta(hours=int(ev_data.duration[ind] if isinstance(ev_data.duration, list) else ev_data.duration))

            s_event = await guild.create_scheduled_event(
                name=ev_data.name,
                start_time=date,
                end_time=end_time,
                entity_type=discord.EntityType.voice,
                channel=channel,
                image=img if img else discord.utils.MISSING,
                privacy_level=discord.PrivacyLevel.guild_only,
            )
            id_list.append(s_event.id)
        else:
            id_list.append(-1)

    return id_list


class InternalEvents(AutocompleteMixin, commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.get_cog("Database")
        self.autocomplete_setup(self.bot)


    async def owned_events_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        owned = await self.db.get_by_user(interaction.guild_id, interaction.user.id)
        return [ app_commands.Choice(name=item, value=item) for item in owned if item.__contains__(current) or current.__len__() == 0]


    @commands.Cog.listener()
    async def on_event_channel_creation(self, interaction: discord.Interaction, event: Event):
        section = None
        guild = interaction.guild

        f_category = discord.utils.get(interaction.guild.categories, name=event.section)

        overwrites = discord.utils.MISSING

        if event.is_private:
            master_perms = discord.PermissionOverwrite(view_channel=True, manage_threads=True, manage_messages=True, manage_channels=True)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: master_perms,
                guild.me: master_perms
            }

        if f_category is None:
            section = await guild.create_category(event.section, overwrites=overwrites)
            text_channel = await guild.create_text_channel(event.text_channel, category=section, overwrites=overwrites)
            voice_channel = await guild.create_voice_channel(event.voice_channel, category=section, overwrites=overwrites)
        else:
            perms = f_category.permissions_for(interaction.user)
            if not perms.view_channel:
                await interaction.followup.send(
                    "You don't have permission to create channels in that section.", ephemeral=True
                )
                return
            text_channel = await guild.create_text_channel(event.text_channel, category=f_category, overwrites=overwrites)
            voice_channel = await guild.create_voice_channel(event.voice_channel, category=f_category, overwrites=overwrites)

        event.section = f_category.id if f_category else section.id
        event.text_channel = text_channel.id
        event.voice_channel = voice_channel.id

        interaction.client.dispatch("event_full_creation_scheduling", interaction, event)


    @commands.Cog.listener()
    async def on_event_full_creation_scheduling(self, interaction: discord.Interaction, event: Event):
        try:
            guild = interaction.guild

            c_channel = guild.get_channel(event.voice_channel)

            event.int_evt = await scheduled_events(event, guild, c_channel)

            if event.role is None:
                event.role = await role_creation(interaction, event)

            role = guild.get_role(event.role)

            if event.is_private and event.created_for_event:
                await guild.get_channel(event.section).set_permissions(role, view_channel=True)
                await guild.get_channel(event.text_channel).set_permissions(role, view_channel=True)
                await c_channel.set_permissions(role, view_channel=True)

            interaction.client.dispatch("ext_event_creation", interaction, event)

        except Exception as e:
            print(f"Listener error: {e!r}")


    @commands.Cog.listener()
    async def on_notify_invitations(self, interaction: discord.Interaction, event: Event):
        guild = interaction.guild
        assert all(isinstance(m, discord.Member) for m in event.members)

        channel = guild.get_channel(event.text_channel or event.voice_channel)

        flag = channel.overwrites_for(guild.default_role).view_channel or channel.category.overwrites_for(guild.default_role).view_channel

        if flag is None:
            cleaned_mentions = (", ".join(f"<@{user.id}>" for user in event.members if user.id is not interaction.user.id))
            await channel.send(content=f"Welcome! this is the official channel of <@&{event.role}>\n <@{interaction.user.id}> has invited you to join\n" + cleaned_mentions)
        else:
            await channel.send(content=f"Welcome! this is the official channel of <@&{event.role}>\n created by: <@{interaction.user.id}>\n currently waiting for people to join :p")

        if event.int_evt:
           if event.int_evt[0] > 0:
               sch_event = await guild.fetch_scheduled_event(event.int_evt[0])
               if sch_event:
                   await channel.send(f"{sch_event.url}")


    @commands.Cog.listener()
    async def on_quick_creation(self, guild:discord.Guild|int, event: Event, internal_data=None, interaction: discord.Interaction | None=None, admin:bool=False):
        if isinstance(guild, int):
            guild = self.bot.get_guild(guild)

        if internal_data is None:
            internal_data = await self.db.get_internal_data(guild.id, event.owner, event.name)

        if internal_data is None and interaction:
            await interaction.followup.send(content="Event has not been set up for this command :c", ephemeral=True)

        if internal_data.get("vc_id"):
            c_channel = guild.get_channel(internal_data.get("vc_id"))

            event.description = internal_data.get("desc")
            event.image = internal_data.get("thumbnail", None)

            internal_id = await scheduled_events(event, guild, c_channel)

            dispatcher = interaction.client if interaction else self.bot
            u_id = interaction.user.id if interaction else -1

            dispatcher.dispatch(
                "ext_event_q_creation",
                guild,
                event,
                internal_id,
                interaction,
                admin
            )


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


    @commands.Cog.listener()
    async def on_scheduled_event_delete(self, event):
        success = await self.db.delete_via_manual(event.guild_id, event.id)
        if success:
            await self.bot.get_cog("ExternalCalendar").update_calendar(event.guild_id, None)


    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        await self.db.delete_assigned_adv(channel.guild.id, channel)


    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        await self.db.delete_assigned_adv(role.guild.id, role)


    @app_commands.command(name="attach_image", description="Add an image to an event you own")
    @app_commands.autocomplete(target=owned_events_autocomplete)
    @role_check()
    async def add_image(self, interaction: discord.Interaction, target: str, image: discord.Attachment):
        await defer(interaction)

        file_name, image_bytes = await process_image(image, interaction)

        await save_thumbnail(file_name, image_bytes)

        if await self.db.update_thumbnail(interaction.guild_id, interaction.user.id, target, file_name):
            internal_ids = await self.db.get_all_internal_id(interaction.guild_id, interaction.user.id, target)
            t_guild: discord.Guild = self.bot.get_guild(interaction.guild_id)
            if internal_ids and len(internal_ids) > 0:
                for i_id in internal_ids:
                    await t_guild.get_scheduled_event(i_id).edit(image=image_bytes)

        await interaction.followup.send("done", Ephemeral=True)


    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="associated_role", description="Assign which role is allowed to use commands")
    async def managerial_role(self, interaction:discord.Interaction, role:discord.Role):
        await defer(interaction)
        if await self.db.update_associated_role(interaction.guild_id, role.id):
            await interaction.followup.send(f"Assigned Role Updated To <@&{role.id}>")
        else:
            await interaction.followup.send("Role assignment failed")


    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="remove_associated", description="Remove the requirement for a role when using commands")
    async def remove_role(self, interaction:discord.Interaction):
        await defer(interaction)
        if await self.db.delete_assigned_role(interaction.guild_id):
            await interaction.followup.send(f"No role is associated with the use of this bot now")
        else:
            await interaction.followup.send("There was no role associated with it already")


async def setup(bot: commands.Bot):
    await bot.add_cog(InternalEvents(bot))