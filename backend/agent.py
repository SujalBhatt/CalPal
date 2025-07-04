from dotenv import load_dotenv
load_dotenv()

import os
import google.generativeai as genai
from calendar_utils import create_event, get_free_slots, get_calendar_service, TEST_CALENDAR_ID
import datetime
import re
from dateutil import parser as dateparser
import pytz

# Read multiple API keys from .env
GEMINI_API_KEYS = os.getenv('GEMINI_API_KEYS', '').split(',')
GEMINI_API_KEYS = [k.strip() for k in GEMINI_API_KEYS if k.strip()]
if not GEMINI_API_KEYS:
    raise ValueError('No Gemini API keys found in .env!')

model: genai.GenerativeModel | None = None
current_key_index = 0

def set_gemini_key(index):
    global model
    genai.configure(api_key=GEMINI_API_KEYS[index])
    model = genai.GenerativeModel('models/gemini-1.5-flash')

set_gemini_key(0)

def extract_booking_info(user_message):
    """
    Use Gemini to extract summary, date, start time, and end time from the user's message.
    Returns a dict with keys: summary, date, start_time, end_time (all as strings or None).
    """
    global model
    # Get current date for reference
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    current_day = datetime.datetime.now().strftime('%A')  # Monday, Tuesday, etc.
    
    prompt = f"""
    Extract the following information from the user's message for booking a calendar event:
    - Event summary (title) - what the meeting/appointment is about
    - Date (YYYY-MM-DD format)
    - Start time (24h format, HH:MM)
    - End time (24h format, HH:MM)
    
    IMPORTANT: Today is {current_date} ({current_day}). Use this as the reference for calculating relative dates.
    
    TIME CONVERSION RULES:
    - "2pm" or "2:00 pm" → "14:00"
    - "10am" or "10:00 am" → "10:00"
    - "3:30pm" → "15:30"
    - "9:15am" → "09:15"
    - "14:30" (already 24h) → "14:30"
    
    Examples:
    - "Book me a meeting with John tomorrow at 2pm" → summary: "Meeting with John", date: {current_date} + 1 day, start_time: "14:00", end_time: "15:00" (default 1 hour)
    - "Schedule a call about the project for Friday at 3pm" → summary: "Project call", date: next Friday from {current_date}, start_time: "15:00", end_time: "16:00"
    - "summary: discussion about pay date: 03-07-2025 start_time: 10:00 am end_time: 10:20 am" → summary: "discussion about pay", date: "2025-07-03", start_time: "10:00", end_time: "10:20"
    
    If any information is missing, return null for that field.
    For relative dates like "tomorrow", "next Monday", calculate the actual date based on today ({current_date}).
    For times without duration, assume 1 hour duration.
    
    User message: {user_message}
    Respond in JSON with keys: summary, date, start_time, end_time.
    """
    if model is None:
        set_gemini_key(current_key_index)
    if model is None:
        raise RuntimeError("Gemini model could not be initialized")
    response = model.generate_content(prompt)
    print('Gemini extraction raw response:', response.text)  # <-- Debug print
    import json
    raw = response.text.strip()
    
    # Remove code block wrappers if present
    if raw.startswith('```'):
        lines = raw.split('\n')
        # Find the JSON content between the code block markers
        json_lines = []
        in_json = False
        for line in lines:
            if line.strip().startswith('```'):
                if in_json:
                    break  # End of JSON block
                else:
                    in_json = True
                    continue
            if in_json:
                json_lines.append(line)
        raw = '\n'.join(json_lines).strip()
    
    # Try to find JSON object in the response
    try:
        # Look for the first { and last } to extract just the JSON
        start = raw.find('{')
        end = raw.rfind('}') + 1
        if start != -1 and end != 0:
            json_str = raw[start:end]
            info = json.loads(json_str)
            print(f"Parsed JSON: {info}")  # Debug print
        else:
            raise ValueError("No JSON object found")
    except Exception as e:
        print(f"JSON parsing error: {e}")  # Debug print
        info: dict[str, str | None] = {"summary": None, "date": None, "start_time": None, "end_time": None}
    
    # Fallback: try to parse date/time if not in ISO format
    if info['date']:
        try:
            dt = dateparser.parse(info['date'], dayfirst=False, yearfirst=True)
            info['date'] = dt.strftime('%Y-%m-%d')
        except Exception:
            info['date'] = None
    
    # Improved time parsing
    for k in ['start_time', 'end_time']:
        if info.get(k):  # Use .get() to safely check if key exists and has a value
            try:
                # First try to parse as a time string
                time_str = str(info[k]).strip()
                print(f"Parsing time '{time_str}' for {k}")  # Debug print
                
                # Handle common time formats
                if 'pm' in time_str.lower() or 'am' in time_str.lower():
                    # Parse 12-hour format
                    parsed_time = dateparser.parse(time_str)
                    info[k] = parsed_time.strftime('%H:%M')
                    print(f"Converted {time_str} to {info[k]}")  # Debug print
                else:
                    # Try to parse as 24-hour format
                    parsed_time = dateparser.parse(time_str)
                    info[k] = parsed_time.strftime('%H:%M')
                    print(f"Parsed {time_str} as {info[k]}")  # Debug print
            except Exception as e:
                print(f"Time parsing error for {k}: {e}")  # Debug print
                info[k] = None
    
    print(f"Final extracted info: {info}")  # Debug print
    return info

def chat_with_agent(user_message):
    import json
    global current_key_index, model
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    current_day = datetime.datetime.now().strftime('%A')

    prompt = f"""
You are CalPal, a smart AI calendar assistant. Today is {current_date} ({current_day}).

Classify the user's message and extract any useful information.

### INTENT types:
- "book" → user wants to schedule an appointment.
- "check_availability" → user is asking if a time is free (but not booking).
- "ask_slots" → user wants to know all available slots for a day.
- "confirm_booking" → user is confirming an earlier suggested time.
- "smalltalk" → general conversation or greeting.
- "unknown" → intent is unclear.

### Extraction goals:
- summary → short title of the event.
- date → in YYYY-MM-DD format (resolve "tomorrow", "next Monday", etc. using today's date).
- start_time / end_time → in 24h format (HH:MM), assume 1 hour duration if only start_time is provided.

Respond ONLY in JSON like this:
{{
  "intent": "...",
  "summary": "...",
  "date": "...",
  "start_time": "...",
  "end_time": "..."
}}

User message: {user_message}
"""

    # Handle key rotation
    for _ in range(len(GEMINI_API_KEYS)):
        try:
            if model is None:
                set_gemini_key(current_key_index)
            response = model.generate_content(prompt)
            break
        except Exception as e:
            if 'quota' in str(e).lower() or '429' in str(e):
                current_key_index = (current_key_index + 1) % len(GEMINI_API_KEYS)
                set_gemini_key(current_key_index)
                continue
            else:
                print(f"Gemini API error: {e}")
                return "Sorry, I had trouble processing your request."

    raw = response.text.strip()
    start = raw.find('{')
    end = raw.rfind('}') + 1
    if start == -1 or end == -1:
        return "Sorry, I couldn't understand your request."

    try:
        parsed = json.loads(raw[start:end])
    except Exception as e:
        print("JSON parsing error:", e)
        return "Sorry, I couldn't understand that. Could you rephrase?"

    intent = parsed.get("intent", "unknown")
    summary = parsed.get("summary")
    date_str = parsed.get("date")
    start_time = parsed.get("start_time")
    end_time = parsed.get("end_time")

    # For easier conversion
    local_tz = pytz.timezone('Asia/Kolkata')

    if intent == "smalltalk":
        return "Hi! I'm CalPal — your calendar assistant. Need help finding or booking a slot?"

    if intent == "ask_slots" and date_str:
        day = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        start_dt = day.replace(hour=8, minute=0)
        end_dt = day.replace(hour=20, minute=0)
        slots = get_free_slots(start_dt, end_dt, 60)
        if slots:
            reply = f"Here are 1-hour slots available on {date_str}:\n"
            reply += "\n".join([f"- {s[0].strftime('%I:%M %p')} to {s[1].strftime('%I:%M %p')}" for s in slots])
        else:
            reply = f"Sorry, no free 1-hour slots available on {date_str}."
        return reply

    if intent == "check_availability" and date_str and start_time and end_time:
        start_dt = local_tz.localize(datetime.datetime.fromisoformat(f"{date_str}T{start_time}"))
        end_dt = local_tz.localize(datetime.datetime.fromisoformat(f"{date_str}T{end_time}"))
        service = get_calendar_service()
        events = service.events().list(
            calendarId=TEST_CALENDAR_ID,
            timeMin=start_dt.isoformat(),
            timeMax=end_dt.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute().get('items', [])

        if events:
            return f"❌ That time slot ({start_time}–{end_time}) on {date_str} is already booked."
        else:
            return f"✅ Yes, {start_time} to {end_time} on {date_str} is available."

    if intent == "confirm_booking" or intent == "book":
        if not all([date_str, start_time]):
            return "To book your appointment, please tell me the date and start time."

        if not end_time:
            # Default 1 hour
            start_dt = datetime.datetime.fromisoformat(f"{date_str}T{start_time}")
            end_dt = (start_dt + datetime.timedelta(hours=1)).strftime('%H:%M')
            end_time = end_dt

        start_dt = local_tz.localize(datetime.datetime.fromisoformat(f"{date_str}T{start_time}"))
        end_dt = local_tz.localize(datetime.datetime.fromisoformat(f"{date_str}T{end_time}"))

        # Check conflicts
        service = get_calendar_service()
        events = service.events().list(
            calendarId=TEST_CALENDAR_ID,
            timeMin=start_dt.isoformat(),
            timeMax=end_dt.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute().get('items', [])

        if events:
            alt_slots = get_free_slots(
                start_dt.replace(hour=8, minute=0),
                start_dt.replace(hour=20, minute=0),
                (end_dt - start_dt).seconds // 60
            )
            suggestion = "\n".join([f"- {s[0].strftime('%I:%M %p')} to {s[1].strftime('%I:%M %p')}" for s in alt_slots[:3]])
            return f"❌ That time is already booked.\nHere are some alternatives:\n{suggestion or 'No slots left today.'}"

        event = create_event(summary or "Appointment", start_dt, end_dt)
        return f"✅ Your event '{summary or 'Appointment'}' is booked on {date_str} from {start_time} to {end_time}!"

    return "I'm not sure what you meant. Could you clarify whether you're checking, booking, or just chatting?" 