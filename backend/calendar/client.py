import asyncio
from datetime import datetime, timezone

from googleapiclient.discovery import build

from gmail.oauth import get_credentials


async def get_calendar_service():
    creds = await get_credentials()
    service = build("calendar", "v3", credentials=creds)
    return service


async def insert_event(
    summary: str,
    start_dt: datetime,
    end_dt: datetime,
    attendee_emails: list[str],
    timezone: str = "Asia/Kolkata",
) -> dict:
    service = await get_calendar_service()

    attendees = [{"email": e} for e in attendee_emails if e]
    event_body = {
        "summary": summary,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": timezone,
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": timezone,
        },
        "attendees": attendees,
        "conferenceData": {
            "createRequest": {
                "requestId": f"asdr-{start_dt.timestamp()}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: service.events().insert(
            calendarId="primary",
            body=event_body,
            conferenceDataVersion=1,
            sendUpdates="all",
        ).execute(),
    )
    return result


async def list_events(time_min: datetime, time_max: datetime) -> list[dict]:
    service = await get_calendar_service()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: service.events().list(
            calendarId="primary",
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute(),
    )
    return result.get("items", [])
