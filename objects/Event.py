import datetime as dt
from dataclasses import field
from typing import List, Union, Any
from zoneinfo import ZoneInfo
import discord


def format_dates(dates:str, start_time:int=12, tmz_s=None):
    date_list: list[Any] = dates.split(",")
    current = dt.datetime.now()
    tz = ZoneInfo(tmz_s or "America/Merida")
    for i, d in enumerate(date_list):
        try:
            spl = [int(itm.strip()) for itm in d.split("-")]
            if len(spl) == 1:
                date_stamp = dt.datetime(current.year, current.month, spl[0], hour=start_time, tzinfo=tz)
            elif len(spl) == 2:
                date_stamp = dt.datetime(current.year, spl[0], spl[1], hour=start_time, tzinfo=tz)
            else:
                date_stamp = dt.datetime(spl[0], spl[1], spl[2], hour=start_time, tzinfo=tz)
            date_list[i] = date_stamp
        except TypeError:
            raise TypeError()
        except ValueError:
            raise ValueError()
    return date_list


class Event:

    def __init__(self, owner:int, name:str, description:str, dates:str|list[dt.datetime], starts:int = None, duration:int|list[int] = None, mode:str = None, colour:List[str] = None, timezone:str = None, image:tuple[str, bytes]= None):
        # Unique information saved on its own folder, relational style
        self.owner = owner

        # Individual information saved also on its own folder
        self.name = name
        self.description = description
        # Saved on the above folder, divided because these are important to be reflected on the calendar
        self.color = colour
        self.custom_modified = False
        self.custom_set_1 = None
        self.custom_set_2 = None
        self.custom_gradient = None
        self.frequency = int(mode)

        # Saved on a general ID tracked list of dates, based on server
        self.dates = format_dates(dates, start_time=starts, tmz_s=timezone) if isinstance(dates, str) else dates
        self.starts = starts
        self.duration = duration

        # for channel event functions
        self.section = None
        self.text_channel = None
        self.voice_channel = None
        self.created_for_event = None
        self.is_private = False

        self.role = None
        self.members: List[Union[discord.Member, discord.User]] = []
        self.int_evt = []

        self.image = image

        # Vestigial, ignore them until further notice
        # self.recurrence = recurrence
        # self.attendees = attendee


    def __str__(self):
        return (f"Owner: {self.owner}, Summary: {self.name}, "
                f"Location: {self.location}, Description: {self.description}, Color: {self.color}, "
                f"Frequency: {self.frequency}, Dates: {self.dates}, Starts: {self.starts}, Duration: {self.duration}, "
                f"Members: {self.members}"
                f"Section: {self.section}, Text_Channel: {self.text_channel}, Voice_Channel: {self.voice_channel}")


    def owner_check(self, owner: discord.User):
        if owner not in self.members:
           self.members = self.members + [owner]


    def check_adv_present(self):
        return isinstance(self.section, int) or (isinstance(self.text_channel, int) or isinstance(self.voice_channel, int))

