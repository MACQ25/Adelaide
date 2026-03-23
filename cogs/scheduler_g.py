import os.path
import discord
from discord.ext import commands
import datetime as dt
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = ["https://www.googleapis.com/auth/calendar"]
SERVICE_ACCOUNT_FILE = "./secrets/gApiToken.json"
ID_TARGET = open("./secrets/targetCalendar.tkn").readline().strip()

class Event:

    """
    Google colors => Discord ones:
    'Tomato Red' - Dark Red
    'Bubblegum Pink' - Fuchsia
    'Mandarin Orange' - Orange
    'Egg Yellow' - Gold
    'Emerald Green' - Green
    'Moss Green' - Dark Green
    'Turquoise Blue' - Blue
    'Blueberry Blue' - Dark Blue
    'Lavender' - og_blurple
    'Deep Purple' - Dark Purple
    'Graphite' - Dark Grey
    """

    COLOR_TRANS = {
        "#992D22" : 11,
        "#EB459E" : 4,
        "#E67E22" : 6,
        "#F1C40F" : 5,
        "#2ECC71" : 2,
        "#1F8B4C" : 10,
        "#3498DB" : 7,
        "#206694" : 9,
        "#7289DA" : 1,
        "#71368A" : 3,
        "#607d8b" : 8,
    }

    def __init__(self, name:str, description:str, colour:str, start:dt.datetime, location:str = "The Interwebs", recurrence:tuple = tuple(), attendees:tuple = tuple()):
        self.summary = name
        self.location = location
        self.description = description
        self.colorId = self.COLOR_TRANS[colour]
        self.start = {
            "dateTime": dt.datetime.now().isoformat() + "Z",
            "timeZone": "UTC"
        }
        self.end = self.start
        self.recurrence = recurrence
        self.attendees = attendees


class CalendarG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    def setup_service(self):
        return build("calendar", "v3", credentials=self.creds)

    @commands.command(name="schedule", description="Create a new event on the calendar and update display")
    async def make_event(self, ctx, *, name: str, desc: str, colour: discord.Colour, start: dt.datetime):
        try:
            service = self.setup_service()

            print("scheduling", colour)

            toSchedule = Event(name=name, description=desc, colour=colour.__str__() , start=start).__dict__

            event = service.events().insert(calendarId=ID_TARGET, body=toSchedule).execute

        except HttpError as error:
            print("An Error Has Occurred!, ", error)

    @commands.command(name="list")
    async def get_events(self, ctx):
        try:
            service = self.setup_service()

            now = dt.datetime.now().isoformat() + "Z"

            event_result = \
                (service.events()
                 .list(
                    calendarId=ID_TARGET,
                    timeMin=now,
                    maxResults=10,
                    singleEvents=True,
                    orderBy="startTime"
                ).execute())

            events = event_result.get("items", [])

            if not events:
                print("no events found")
                return
            for event in events:
                start = event["start"].get("datetime", event["start"].get("date"))
                print(start, event["summary"])

        except HttpError as error:
            print("An Error Has Occurred!, ", error)


async def setup(bot):
    await bot.add_cog(CalendarG(bot))