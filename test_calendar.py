import os, json, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'service_account.json'  # Update if your filename is different
CALENDAR_ID = '370a00f5d5068f7a6936eee2a1115ed00466f6d2555cd6efafe4358ff2ffd13b@group.calendar.google.com'

with open(SERVICE_ACCOUNT_FILE) as f:
    info = json.load(f)
creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
service = build('calendar', 'v3', credentials=creds)

now = datetime.datetime.utcnow()
start = now.replace(hour=8, minute=0, second=0, microsecond=0)
end = now.replace(hour=20, minute=0, second=0, microsecond=0)
events = service.events().list(
    calendarId=CALENDAR_ID,
    timeMin=start.isoformat() + 'Z',
    timeMax=end.isoformat() + 'Z',
    singleEvents=True,
    orderBy='startTime'
).execute()
print(events)