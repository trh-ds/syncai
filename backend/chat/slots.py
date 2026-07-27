from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from config import settings
from models import Meeting


def _parse_hours(working_hours: str) -> tuple[int, int]:
    start, end = working_hours.split("-")
    return int(start.split(":")[0]), int(end.split(":")[0])


async def generate_slots(db, existing_meetings: list[Meeting], window_start: datetime | None = None, retry_count: int = 0) -> list[str]:
    tz = ZoneInfo(settings.chat_tz)
    start_hour, end_hour = _parse_hours(settings.chat_working_hours)

    if window_start is None:
        base = datetime.now(tz) + timedelta(days=1)
    else:
        base = window_start

    if retry_count > 0:
        base += timedelta(days=retry_count)

    # Collect existing meeting times to avoid conflicts
    conflict_starts: set[str] = set()
    for m in existing_meetings:
        if m.start_at:
            conflict_starts.add(m.start_at.isoformat())

    slots: list[str] = []
    day_offset = 0
    while len(slots) < 3 and day_offset < 15:
        day = base + timedelta(days=day_offset)
        day_offset += 1

        if day.weekday() >= 5:  # Saturday=5, Sunday=6
            continue

        for hour in range(start_hour, end_hour):
            slot_dt = day.replace(hour=hour, minute=0, second=0, microsecond=0)
            slot_iso = slot_dt.isoformat()

            if slot_iso in conflict_starts:
                continue

            if slot_dt <= datetime.now(tz):
                continue

            slots.append(slot_iso)
            if len(slots) >= 3:
                break

    while len(slots) < 3:
        # fallback: generate farther into the future
        fallback = base + timedelta(days=day_offset)
        day_offset += 1
        if fallback.weekday() >= 5:
            continue
        for hour in range(start_hour, end_hour):
            slot_dt = fallback.replace(hour=hour, minute=0, second=0, microsecond=0)
            if slot_dt <= datetime.now(tz):
                continue
            slots.append(slot_dt.isoformat())
            if len(slots) >= 3:
                break

    return slots
