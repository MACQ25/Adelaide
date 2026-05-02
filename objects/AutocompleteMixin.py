import zoneinfo
import discord
from discord import app_commands
from discord.ext import commands


class AutocompleteMixin:
    def setup_db(self, bot):
        self.db = bot.get_cog("Database")


    async def owned_events_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        owned = await self.db.get_by_user(interaction.guild_id, interaction.user.id)
        return [ app_commands.Choice(name=item, value=item) for item in owned if item.__contains__(current) or current.__len__() == 0]


    async def event_dates_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        evt_name = interaction.namespace.name
        scheduled = await self.db.get_by_class(interaction.guild_id, evt_name)

        scheduled = [ val.get('date').strftime("%B %d of %Y") for val in scheduled ]

        entered_dates = [d.strip() for d in interaction.namespace.dates.split(",")]
        registered_values = [str(i) for i, n in enumerate(scheduled) if n in entered_dates]
        confirmed = [scheduled[int(i)] for i in registered_values]
        query = next((x for x in entered_dates if x not in confirmed), None)

        # [ app_commands.Choice(name=str(item[1]), value=str(item[0])) for item in scheduled if str(item[1]).__contains__(current) or current.__len__() == 0 ]

        choices = []

        if len(registered_values) > 0:
            choices.append(app_commands.Choice(
                name=', '.join(confirmed),
                value=', '.join(registered_values)
            ))

        for ind, item in enumerate(scheduled):
            if item in confirmed or str(ind) in registered_values:
                continue

            if query and query not in item:
                continue

            if len(registered_values) > 0:
                full_value = f"{",".join(registered_values)}, {ind}"

                choices.append(app_commands.Choice(
                    name=f'{", ".join(confirmed)}, {item}',
                    value=full_value,
                ))
            else:
                choices.append(app_commands.Choice(
                    name=item,
                    value= str(ind)
                ))

        return choices


    async def timezone_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        zones = sorted(zoneinfo.available_timezones())
        return [ app_commands.Choice(name=tz, value=tz) for tz in zones if current.lower() in tz.lower()][:25]
