import logging
from datetime import datetime, timedelta, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from core.config import settings
from services.gmail_client import _creds as gmail_creds

logger = logging.getLogger("calendar")


def _calendar_creds():
    c = gmail_creds()
    if "https://www.googleapis.com/auth/calendar" not in c.scopes:
        c = Credentials(
            token=None,
            refresh_token=settings.GMAIL_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GMAIL_CLIENT_ID,
            client_secret=settings.GMAIL_CLIENT_SECRET,
            scopes=[
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/gmail.send",
            ],
        )
        c.refresh(Request())
    return c


def _service():
    return build("calendar", "v3", credentials=_calendar_creds())


def get_availability(days: int = 7) -> list[dict]:
    """Return free/busy info for the next N days as list of available 30-min slots."""
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)

    try:
        svc = _service()
        body = {
            "timeMin": now.isoformat(),
            "timeMax": end.isoformat(),
            "items": [{"id": settings.GMAIL_USER_EMAIL}],
        }
        result = svc.freebusy().query(body=body).execute()
    except HttpError as e:
        logger.error("Calendar freebusy error: %s", e)
        return []

    busy = []
    for cal in result.get("calendars", {}).values():
        for slot in cal.get("busy", []):
            busy.append((slot["start"], slot["end"]))

    slots = []
    cursor = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    work_start = 9
    work_end = 17

    for day_offset in range(days):
        day = cursor + timedelta(days=day_offset)
        for hour in range(work_start, work_end):
            slot_start = day.replace(hour=hour)
            slot_end = slot_start + timedelta(minutes=30)
            if slot_start < now:
                continue
            if slot_start.weekday() >= 5:
                continue
            blocked = False
            for bs, be in busy:
                bs_dt = datetime.fromisoformat(bs.replace("Z", "+00:00"))
                be_dt = datetime.fromisoformat(be.replace("Z", "+00:00"))
                if slot_start < be_dt and slot_end > bs_dt:
                    blocked = True
                    break
            if not blocked:
                slots.append({
                    "start": slot_start.isoformat(),
                    "end": slot_end.isoformat(),
                })
    return slots


def book_event(
    summary: str,
    start: datetime,
    end: datetime,
    attendee_email: str,
    attendee_name: str,
) -> dict | None:
    """Create a Google Calendar event with an attendee. Returns event dict or None."""
    try:
        svc = _service()
        event = {
            "summary": summary,
            "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
            "attendees": [{"email": attendee_email, "displayName": attendee_name}],
        }
        result = svc.events().insert(calendarId="primary", body=event, sendUpdates="all").execute()
        return {
            "id": result["id"],
            "summary": result["summary"],
            "start": result["start"]["dateTime"],
            "end": result["end"]["dateTime"],
        }
    except HttpError as e:
        logger.error("Calendar book error: %s", e)
        return None
