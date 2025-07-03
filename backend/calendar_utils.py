import datetime
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pytz

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), '../service_account.json')

# Set your test calendar ID here (from Google Calendar settings)
TEST_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID', 'primary')

def get_calendar_service():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=credentials)
    return service

def get_free_slots(start_time, end_time, duration_minutes=30):
    service = get_calendar_service()
    events_result = service.events().list(
        calendarId=TEST_CALENDAR_ID,
        timeMin=start_time.isoformat(),
        timeMax=end_time.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    # Build a list of busy intervals
    busy = []
    for event in events:
        ev_start = event['start'].get('dateTime', event['start'].get('date'))
        ev_end = event['end'].get('dateTime', event['end'].get('date'))
        if ev_start and ev_end:
            busy.append((datetime.datetime.fromisoformat(ev_start.replace('Z','+00:00')),
                         datetime.datetime.fromisoformat(ev_end.replace('Z','+00:00'))))
    busy.sort()
    print(f"Busy intervals: {busy}")  # Debug print

    # Find free slots between busy intervals
    free_slots = []
    current = start_time
    while current + datetime.timedelta(minutes=duration_minutes) <= end_time:
        next_slot_end = current + datetime.timedelta(minutes=duration_minutes)
        overlap = False
        for b_start, b_end in busy:
            if (current < b_end and next_slot_end > b_start):
                overlap = True
                # Move current to the end of this busy interval (skip all overlapping slots)
                if b_end > current:
                    current = b_end
                break
        if not overlap:
            free_slots.append((current, next_slot_end))
            print(f"Free slot found: {current} to {next_slot_end}")  # Debug print
            current = next_slot_end
    return free_slots

def create_event(summary, start_time, end_time, description=None):
    service = get_calendar_service()
    local_tz = pytz.timezone('Asia/Kolkata')  # Asia/NewDelhi is not a valid tz, use Asia/Kolkata

    # If start_time/end_time are naive, localize them
    if start_time.tzinfo is None:
        start_time = local_tz.localize(start_time)
    if end_time.tzinfo is None:
        end_time = local_tz.localize(end_time)

    event = {
        'summary': summary,
        'start': {'dateTime': start_time.isoformat(), 'timeZone': 'Asia/Kolkata'},
        'end': {'dateTime': end_time.isoformat(), 'timeZone': 'Asia/Kolkata'},
        'description': description or '',
    }
    created_event = service.events().insert(calendarId=TEST_CALENDAR_ID, body=event).execute()
    return created_event 