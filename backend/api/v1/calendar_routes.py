import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.database import SessionLocal
from models.customer import Customer, Meeting
from services.calendar_service import book_event as cal_book_event
from services.calendar_service import get_availability as cal_availability

router = APIRouter(prefix="/calendar", tags=["calendar"])
logger = logging.getLogger("calendar_routes")


class AvailabilitySlot(BaseModel):
    start: str
    end: str


class BookRequest(BaseModel):
    customer_email: str = Field(min_length=1)
    attendee_name: str = Field(min_length=1)
    start: str = Field(min_length=1)  # ISO 8601


class BookResponse(BaseModel):
    confirmed: bool
    event_id: str | None = None
    start: str
    end: str
    summary: str


@router.get("/availability", response_model=list[AvailabilitySlot])
def availability():
    try:
        return cal_availability(days=7)
    except Exception as e:
        raise HTTPException(status_code=502, detail={"code": "CALENDAR_ERROR", "message": str(e)})


@router.post("/book", response_model=BookResponse)
def book(payload: BookRequest):
    start = datetime.fromisoformat(payload.start)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    end = start + timedelta(minutes=30)

    event = cal_book_event(
        summary=f"Meeting with {payload.attendee_name} ({payload.customer_email})",
        start=start,
        end=end,
        attendee_email=payload.customer_email,
        attendee_name=payload.attendee_name,
    )
    if not event:
        raise HTTPException(status_code=502, detail={"code": "CALENDAR_BOOK_FAILED", "message": "Could not create event"})

    db = SessionLocal()
    try:
        customer = db.query(Customer).filter(Customer.email == payload.customer_email).first()
        meeting = Meeting(
            customer_id=customer.id if customer else None,
            google_event_id=event["id"],
            summary=event["summary"],
            start_time=start,
            end_time=end,
            status="scheduled",
        )
        db.add(meeting)
        if customer:
            customer.lead_score = "hot"
        db.commit()
    finally:
        db.close()

    return BookResponse(
        confirmed=True,
        event_id=event["id"],
        start=start.isoformat(),
        end=end.isoformat(),
        summary=event["summary"],
    )
