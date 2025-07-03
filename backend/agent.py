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
    """
    Optimized: Single Gemini call to handle both booking and chat, with API key rotation.
    """
    global current_key_index, model
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    current_day = datetime.datetime.now().strftime('%A')
    prompt = f"""
    You are CalPal, an AI calendar assistant. Today is {current_date} ({current_day}).
    
    Analyze the user's message and do the following:
    1. If the user wants to book or schedule an appointment/meeting/event, extract:
        - summary (what the event is about)
        - date (YYYY-MM-DD, calculate relative dates like 'tomorrow' or 'next Monday' based on today)
        - start_time (24h format, HH:MM, convert from 12h if needed)
        - end_time (24h format, HH:MM, assume 1 hour if not specified)
        Respond ONLY in JSON with these keys: summary, date, start_time, end_time. If any info is missing, use null.
    2. If the user is just chatting or not booking, respond with a friendly, conversational reply as CalPal.
    
    User message: {user_message}
    
    Examples:
    - "Book me a meeting with John tomorrow at 2pm" → {{"summary": "Meeting with John", "date": "{current_date} + 1 day", "start_time": "14:00", "end_time": "15:00"}}
    - "I need to book a doctor's appointment for next Monday at 11am" → {{"summary": "doctor's appointment", "date": "(next Monday)", "start_time": "11:00", "end_time": "12:00"}}
    - "Hi, how are you?" → Friendly, conversational reply as CalPal.
    """
    for _ in range(len(GEMINI_API_KEYS)):
        try:
            if model is None:
                set_gemini_key(current_key_index)
            if model is None:
                raise RuntimeError("Gemini model could not be initialized")
            response = model.generate_content(prompt)
            break
        except Exception as e:
            if 'quota' in str(e).lower() or '429' in str(e):
                current_key_index = (current_key_index + 1) % len(GEMINI_API_KEYS)
                set_gemini_key(current_key_index)
                continue  # Try next key
            else:
                print(f"Gemini API error: {e}")
                return "Sorry, an error occurred with the AI assistant. Please try again later."
    else:
        return "Sorry, all API keys have reached their quota. Please try again tomorrow!"
    print('Gemini unified response:', response.text)
    import json
    raw = response.text.strip()
    # Try to find JSON object in the response
    start = raw.find('{')
    end = raw.rfind('}') + 1
    if start != -1 and end != 0:
        json_str = raw[start:end]
        try:
            info = json.loads(json_str)
            print(f"Parsed JSON: {info}")
            # If at least one booking field is not null, treat as booking
            if any(info.get(k) for k in ['summary', 'date', 'start_time', 'end_time']):
                # Only ask for missing date, start_time, or end_time
                missing = [k for k in ['date', 'start_time', 'end_time'] if not info.get(k)]
                # If only date is present, list all available slots for that day
                if info.get('date') and not info.get('start_time') and not info.get('end_time'):
                    day = datetime.datetime.strptime(info['date'], '%Y-%m-%d')
                    start_dt = day.replace(hour=8, minute=0)
                    end_dt = day.replace(hour=20, minute=0)
                    free_slots = get_free_slots(start_dt, end_dt, 60)  # 60 min slots
                    if free_slots:
                        suggestions = '\n'.join([
                            f"- {slot[0].strftime('%I:%M %p')} to {slot[1].strftime('%I:%M %p')}" for slot in free_slots
                        ])
                        return f"Here are the available slots for {info['date']} (1 hour each):\n{suggestions}"
                    else:
                        return f"Sorry, there are no free slots available for {info['date']}."
                if missing:
                    missing_str = ', '.join(missing)
                    return f"To book your appointment, please provide: {missing_str}."
                # If summary is missing, use a default
                if not info.get('summary'):
                    info['summary'] = 'Appointment'
                # All info present, try to book
                try:
                    start_dt = datetime.datetime.fromisoformat(f"{info['date']}T{info['start_time']}")
                    end_dt = datetime.datetime.fromisoformat(f"{info['date']}T{info['end_time']}")
                except Exception:
                    return "Sorry, I couldn't understand the date or time. Please use YYYY-MM-DD for date and HH:MM for time."
                # Ensure start_dt and end_dt are timezone-aware
                local_tz = pytz.timezone('Asia/Kolkata')
                if start_dt.tzinfo is None:
                    start_dt = local_tz.localize(start_dt)
                if end_dt.tzinfo is None:
                    end_dt = local_tz.localize(end_dt)
                # Fetch all events for the day for conflict checking
                service = get_calendar_service()
                day_start = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = start_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
                events_result = service.events().list(
                    calendarId=TEST_CALENDAR_ID,
                    timeMin=day_start.isoformat(),
                    timeMax=day_end.isoformat(),
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                events = events_result.get('items', [])
                for event in events:
                    ev_start = event['start'].get('dateTime', event['start'].get('date'))
                    ev_end = event['end'].get('dateTime', event['end'].get('date'))
                    if ev_start and ev_end:
                        ev_start_dt = datetime.datetime.fromisoformat(ev_start.replace('Z','+00:00'))
                        ev_end_dt = datetime.datetime.fromisoformat(ev_end.replace('Z','+00:00'))
                        # Ensure event datetimes are timezone-aware
                        if ev_start_dt.tzinfo is None:
                            ev_start_dt = local_tz.localize(ev_start_dt)
                        if ev_end_dt.tzinfo is None:
                            ev_end_dt = local_tz.localize(ev_end_dt)
                        if (start_dt < ev_end_dt and end_dt > ev_start_dt):
                            # Suggest alternative slots (use slot[0] and slot[1] ONLY)
                            slot_duration = (end_dt - start_dt).seconds // 60
                            free_slots = get_free_slots(start_dt.replace(hour=8, minute=0), start_dt.replace(hour=20, minute=0), slot_duration)
                            suggestions = '\n'.join([
                                f"- {slot[0].strftime('%Y-%m-%d %I:%M %p')} to {slot[1].strftime('%I:%M %p')}" for slot in free_slots[:3]
                            ])
                            return f"That time slot is already booked. Here are some other available slots:\n{suggestions if suggestions else 'No free slots available today.'}"
                event = create_event(info['summary'], start_dt, end_dt)
                return f"Your appointment '{info['summary']}' is booked for {info['date']} from {info['start_time']} to {info['end_time']}!"
            else:
                # Not a booking, treat as chat
                # Remove any JSON from the response and return the rest
                chat_reply = raw[end:].strip()
                if not chat_reply:
                    chat_reply = raw[:start].strip()
                return chat_reply or "I'm here to help!"
        except Exception as e:
            print(f"JSON parsing error: {e}")
            # If parsing fails, treat as chat
            chat_reply = raw[end:].strip()
            if not chat_reply:
                chat_reply = raw[:start].strip()
            return chat_reply or "I'm here to help!"
    else:
        # No JSON found, treat as chat
        return raw or "I'm here to help!" 