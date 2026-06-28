"""
Calendar Service
Phase 6: Google Calendar integration.

Unlike Firestore (which used a service account), Calendar access needs
OAuth — a real user has to grant consent, since we're reading/writing
*their* personal calendar, not a service's own data.

On first run, this opens a browser window asking you to log in and grant
calendar access. After that, a `token.json` file caches your access token
so you won't have to log in every time (it auto-refreshes).
"""

import os
import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Only requesting calendar access — nothing else
SCOPES = ["https://www.googleapis.com/auth/calendar"]

CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"


def get_calendar_service():
    """
    Returns an authenticated Google Calendar API client.
    Handles the OAuth flow on first run, and reuses/refreshes the cached
    token on subsequent runs.
    """
    creds = None

    # Reuse cached token if it exists
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If no valid creds, refresh or run the login flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            # Opens a browser window for you to log in and grant access
            creds = flow.run_local_server(port=0)

        # Cache the token for next time
        with open(TOKEN_FILE, "w") as token_file:
            token_file.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def push_task_to_calendar(title: str, deadline_str: str) -> dict:
    """
    Creates a calendar event for a task at its deadline.
    `deadline_str` must be in the format "YYYY-MM-DD HH:MM" (guaranteed by
    the app's date/time picker inputs). Raises a clear error if no deadline
    was set, rather than silently guessing a time.

    Returns a dict with 'link' (HTML link to view the event) and 'event_id'
    (needed later to update/complete the event when the task is marked done).
    """
    if not deadline_str or not deadline_str.strip():
        raise ValueError("This task has no deadline set, so it can't be added to your calendar yet.")

    service = get_calendar_service()

    try:
        start_time = datetime.datetime.strptime(deadline_str.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        raise ValueError(f"Couldn't understand the deadline format: '{deadline_str}'")

    end_time = start_time + datetime.timedelta(minutes=30)

    event = {
        "summary": title,
        "description": "Created by Last-Minute Life Saver",
        "start": {"dateTime": start_time.isoformat(), "timeZone": "Asia/Kolkata"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "Asia/Kolkata"},
    }

    created_event = service.events().insert(calendarId="primary", body=event).execute()
    return {
        "link": created_event.get("htmlLink", ""),
        "event_id": created_event.get("id", ""),
    }


def mark_event_completed(event_id: str):
    """
    Updates a previously-synced calendar event to show the task is done —
    prefixes the title with ✅ so it's visually obvious in Google Calendar
    without needing to open the app.
    """
    if not event_id:
        return

    service = get_calendar_service()
    event = service.events().get(calendarId="primary", eventId=event_id).execute()

    # Avoid double-prefixing if marked done more than once
    if not event["summary"].startswith("✅"):
        event["summary"] = f"✅ {event['summary']}"

    service.events().update(calendarId="primary", eventId=event_id, body=event).execute()


def get_upcoming_events(max_results: int = 10):
    """
    Fetches the user's upcoming calendar events (not just ones created by
    this app) — used to give the Deadline Negotiator awareness of the
    user's real schedule, not just their task list.

    Returns a list of dicts with 'title' and 'start' keys.
    """
    service = get_calendar_service()
    now = datetime.datetime.utcnow().isoformat() + "Z"

    events_result = service.events().list(
        calendarId="primary",
        timeMin=now,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = events_result.get("items", [])

    return [
        {
            "title": e.get("summary", "(no title)"),
            "start": e["start"].get("dateTime", e["start"].get("date", "")),
        }
        for e in events
    ]