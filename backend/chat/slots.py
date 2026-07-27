from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from config import settings
from gcal.client import list_events


def _parse_hours(hours_str: str) -> tuple[int, int]:
    start_str, end_str = hours_str.split("-")
    return int(start_str.split(":")[0]), int(end_str.split(":")[0])


async def generate_slots(
    db,
    existing_meetings: list,
    window_start: datetime | None = None,
    retry_count: int = 0,
) -> list[str]:
    tz = ZoneInfo(settings.chat_tz)
    start_hour, end_hour = _parse_hours(settings.chat_working_hours)

    now = datetime.now(tz)
    if window_start:
        if window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=tz)
    else:
        window_start = now + timedelta(hours=retry_count * 24)
    if retry_count > 1:
        window_start = window_start + timedelta(days=retry_count - 1)

    candidate_slots: list[datetime] = []
    current_day = window_start.replace(hour=0, minute=0, second=0, microsecond=0)

    while len(candidate_slots) < 3:
        if current_day.weekday() >= 5:  # Saturday=5, Sunday=6
            current_day += timedelta(days=1)
            continue

        slot_time = current_day.replace(hour=start_hour)
        end_time = current_day.replace(hour=end_hour)

        while slot_time + timedelta(minutes=30) <= end_time:
            if slot_time >= window_start:
                candidate_slots.append(slot_time)
                if len(candidate_slots) >= 3:
                    break
            slot_time += timedelta(minutes=30)

        current_day += timedelta(days=1)

    busy_slots = set()
    search_min = window_start - timedelta(days=1)
    search_max = window_start + timedelta(days=7)
    cal_events = await list_events(search_min, search_max)

    for event in cal_events:
        start_str = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
        end_str = event.get("end", {}).get("dateTime") or event.get("end", {}).get("date")
        if start_str and end_str:
            evt_start = datetime.fromisoformat(start_str)
            evt_end = datetime.fromisoformat(end_str)
            if evt_start.tzinfo is None:
                evt_start = evt_start.replace(tzinfo=tz)
            if evt_end.tzinfo is None:
                evt_end = evt_end.replace(tzinfo=tz)
            cursor = evt_start
            while cursor < evt_end:
                busy_slots.add(cursor.replace(minute=0, second=0, microsecond=0))
                busy_slots.add(cursor.replace(minute=30, second=0, microsecond=0))
                cursor += timedelta(minutes=30)

    available: list[str] = []
    for slot in candidate_slots:
        rounded = slot.replace(minute=0, second=0, microsecond=0)
        if rounded not in busy_slots and slot.replace(minute=30, second=0, microsecond=0) not in busy_slots:
            available.append(slot.isoformat())
        if len(available) >= 3:
            break

    if len(available) < 3 and retry_count < 5:
        return await generate_slots(db, existing_meetings, window_start, retry_count + 1)

    return available[:3]
