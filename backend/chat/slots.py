from datetime import datetime, timedelta, timezone

from config import settings
from models import Meeting


def _parse_hours(working_hours: str) -> tuple[int, int]:
    start, end = working_hours.split("-")
    return int(start.split(":")[0]), int(end.split(":")[0])


async def is_slot_available(db, requested_dt: datetime, existing_meetings: list[Meeting] | None = None) -> bool:
    from sqlalchemy import select, and_
    from config import settings

    tz = settings.chat_tz
    start_hour, end_hour = _parse_hours(settings.chat_working_hours)

    if requested_dt.weekday() >= 5:
        return False
    if requested_dt.hour < start_hour or requested_dt.hour >= end_hour:
        return False
    if requested_dt <= datetime.now(timezone.utc):
        return False

    if existing_meetings is None:
        return True

    slot_end = requested_dt + timedelta(minutes=30)
    for m in existing_meetings:
        if m.status == "cancelled":
            continue
        if m.start_at and m.end_at:
            if requested_dt < m.end_at and slot_end > m.start_at:
                return False
    return True


async def generate_slots(db, existing_meetings: list[Meeting], window_start: datetime | None = None, retry_count: int = 0) -> list[str]:
    start_hour, end_hour = _parse_hours(settings.chat_working_hours)

    if window_start is None:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(settings.chat_tz)
        base = datetime.now(tz) + timedelta(days=1)
    else:
        base = window_start

    if retry_count > 0:
        base += timedelta(days=retry_count)

    conflict_starts: set[str] = set()
    for m in existing_meetings:
        if m.start_at:
            conflict_starts.add(m.start_at.isoformat())

    slots: list[str] = []
    day_offset = 0
    while len(slots) < 3 and day_offset < 15:
        day = base + timedelta(days=day_offset)
        day_offset += 1

        if day.weekday() >= 5:
            continue

        for hour in range(start_hour, end_hour):
            slot_dt = day.replace(hour=hour, minute=0, second=0, microsecond=0)
            slot_iso = slot_dt.isoformat()

            if slot_iso in conflict_starts:
                continue

            from zoneinfo import ZoneInfo
            tz = ZoneInfo(settings.chat_tz)
            if slot_dt <= datetime.now(tz):
                continue

            slots.append(slot_iso)
            if len(slots) >= 3:
                break

    while len(slots) < 3:
        fallback = base + timedelta(days=day_offset)
        day_offset += 1
        if fallback.weekday() >= 5:
            continue
        for hour in range(start_hour, end_hour):
            slot_dt = fallback.replace(hour=hour, minute=0, second=0, microsecond=0)
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(settings.chat_tz)
            if slot_dt <= datetime.now(tz):
                continue
            slots.append(slot_dt.isoformat())
            if len(slots) >= 3:
                break

    return slots

