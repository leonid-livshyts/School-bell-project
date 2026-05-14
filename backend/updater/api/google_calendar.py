from pathlib import Path
from os import PathLike

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


root = Path(__name__).resolve().parent
token_file = root / "token.json"


class CalendarAPI:
    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

    def __init__(self, credentials_filename):
        self.service = self.creds = None

        if isinstance(credentials_filename, str):
            credentials_filename = Path(credentials_filename)
        elif not isinstance(credentials_filename, PathLike):
            raise ValueError("Wrong credentials filename")

        if not credentials_filename.is_file():
            raise ValueError(f"File {credentials_filename} does not exists")

        self.credentials_filename = credentials_filename

    def auth(self):
        if token_file.is_file():
            self.creds = Credentials.from_authorized_user_file(str(token_file), CalendarAPI.SCOPES)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_filename), CalendarAPI.SCOPES
                )
                self.creds = flow.run_local_server(port=3200)

            with token_file.open("w") as token:
                token.write(self.creds.to_json())

        return self.creds is not None

    def start(self):
        if self.creds is None:
            raise Exception("Try to authorize first")

        try:
            self.service = build("calendar", "v3", credentials=self.creds)
        except HttpError as err:
            raise Exception("Cannot start a service") from err

    def list_calendars(self):
        if self.service is None:
            raise Exception("Start service first")

        calendar_list = self.service.calendarList()
        result = calendar_list.list().execute()
        return {
            calendar["id"]: calendar["summary"]
            for calendar in result["items"]
        }

    def get_calendar_events(self, calendar_id, start_datetime=None, end_datetime=None):
        if self.service is None:
            raise Exception("Start service first")

        calendar_service = self.service.events()
        result = calendar_service.list(
            calendarId=calendar_id,
            timeMin=start_datetime,
            timeMax=end_datetime,
            # maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        ret_val = []
        for event in result["items"]:
            ret_event = {"title": event["summary"]}
            if "start" in event:
                ret_event["start"] = event["start"]
            if "end" in event:
                ret_event["end"] = event["end"]
            ret_val.append(ret_event)

        return ret_val


