from pathlib import Path
from api.google_calendar import  CalendarAPI
from datetime import datetime, timedelta

credentials_file = Path("credentials.json")
api_obj = CalendarAPI(credentials_file)

if not api_obj.auth():
    raise Exception("NO AUTH")

api_obj.start()
calendars = api_obj.list_calendars()
start_datetime = (datetime.now() - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
finish_datetime = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)

for calendar in calendars:
    events = api_obj.get_calendar_events(
        calendar,
        start_datetime.isoformat() + "Z",
        finish_datetime.isoformat() + "Z"
    )
    print(calendar)
    for event in events:
        print("\t", event)


