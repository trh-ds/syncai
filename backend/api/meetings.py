from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.session import get_db
from events import emit
from models import Lead, Meeting
from schemas import MeetingBookIn, MeetingOut
from gcal.client import insert_event

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


def _meeting_to_out(m: Meeting, lead: Lead | None = None) -> MeetingOut:
    return MeetingOut(
        id=m.id,
        lead_id=m.lead_id,
        source=m.source,
        google_event_id=m.google_event_id,
        title=m.title,
        start_at=m.start_at,
        end_at=m.end_at,
        hangout_link=m.hangout_link,
        status=m.status,
        created_at=m.created_at,
        updated_at=m.updated_at,
        lead_name=f"{lead.first_name or ''} {lead.last_name or ''}".strip() if lead else None,
        lead_email=lead.email if lead else None,
    )


@router.post("/book", response_model=MeetingOut)
async def book_meeting(body: MeetingBookIn, db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, UUID(body.lead_id))
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    event = await insert_event(
        summary=body.title,
        start_dt=body.start_at,
        end_dt=body.end_at,
        attendee_emails=[lead.email] if lead.email else [],
    )

    meeting = Meeting(
        lead_id=lead.id,
        source=body.source,
        google_event_id=event.get("id", ""),
        title=body.title,
        start_at=body.start_at,
        end_at=body.end_at,
        hangout_link=event.get("hangoutLink"),
        status="booked",
    )
    db.add(meeting)

    lead.status = "booked"
    lead.last_activity_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(meeting)
    await db.refresh(lead)

    await emit({
        "type": "meeting_booked",
        "lead_id": str(lead.id),
        "payload": {
            "meeting_id": str(meeting.id),
            "title": body.title,
            "start_at": body.start_at.isoformat(),
            "hangout_link": meeting.hangout_link,
        },
    })

    return _meeting_to_out(meeting, lead)


@router.get("/", response_model=list[MeetingOut])
async def list_meetings(limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Meeting).options(selectinload(Meeting.lead)).order_by(Meeting.created_at.desc()).limit(limit)
    )
    meetings = result.scalars().all()
    return [_meeting_to_out(m, m.lead) for m in meetings]


@router.post("/{meeting_id}/confirm", response_model=MeetingOut)
async def confirm_meeting(meeting_id: UUID, db: AsyncSession = Depends(get_db)):
    meeting = await db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    meeting.status = "confirmed"
    meeting.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(meeting)

    await emit({
        "type": "meeting_confirmed",
        "lead_id": str(meeting.lead_id) if meeting.lead_id else None,
        "payload": {"meeting_id": str(meeting.id)},
    })

    lead = await db.get(Lead, meeting.lead_id) if meeting.lead_id else None
    return _meeting_to_out(meeting, lead)


@router.post("/{meeting_id}/cancel", response_model=MeetingOut)
async def cancel_meeting(meeting_id: UUID, db: AsyncSession = Depends(get_db)):
    meeting = await db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    meeting.status = "cancelled"
    meeting.updated_at = datetime.now(timezone.utc)

    if meeting.lead_id:
        lead = await db.get(Lead, meeting.lead_id)
        if lead and lead.status == "booked":
            lead.status = "contacted"

    await db.commit()
    await db.refresh(meeting)

    await emit({
        "type": "meeting_cancelled",
        "lead_id": str(meeting.lead_id) if meeting.lead_id else None,
        "payload": {"meeting_id": str(meeting.id)},
    })

    lead = await db.get(Lead, meeting.lead_id) if meeting.lead_id else None
    return _meeting_to_out(meeting, lead)
