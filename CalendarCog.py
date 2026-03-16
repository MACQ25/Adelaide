import os.path
import datetime as dt
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]
SERVICE_ACCOUNT_FILE = "secrets/gApiToken.json"
ID_TARGET = open("secrets/targetCalendar.tkn").readline().strip()

print(ID_TARGET)

def main():

    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    try:
        service = build("calendar", "v3", credentials=creds)

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


main()