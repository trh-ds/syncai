from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.session import get_db
from events import emit
from models import Lead, ChatSession, ChatMessage, Meeting
from schemas import ChatMessageIn, ChatMessageOut, MeetingOut
from chat.session import (
    get_or_create_session,
    update_session_state,
    add_chat_message,
    STATE_GREETING,
    STATE_INTENT_CONFIRM,
    STATE_PROPOSE_TIMES,
    STATE_CONFIRM,
    STATE_BOOK,
    STATE_DONE,
    STATE_LOST,
)
from chat.llm_turn import process_turn
from chat.slots import generate_slots
from gcal.client import insert_event

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/message", response_model=ChatMessageOut)
async def chat_message(body: ChatMessageIn, db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, UUID(body.lead_id))
    if not lead:
        lead = Lead(
            email=f"chat-{body.lead_id}@unknown.com",
            source="chat",
            status="captured",
            last_activity_at=datetime.now(timezone.utc),
        )
        db.add(lead)
        await db.flush()

    session = await get_or_create_session(db, lead.id)

    await add_chat_message(db, session.id, "inbound", body.text)

    chat_history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
    )
    chat_history = list(chat_history_result.scalars().all())

    turn = await process_turn(session, body.text, chat_history)
    classification = turn.get("classification", "question")
    reply = turn.get("reply", "")

    proposed_times: list[str] | None = None
    booked_meeting: MeetingOut | None = None

    current_state = session.state

    if classification == "decline" or current_state in (STATE_DONE, STATE_LOST):
        if current_state not in (STATE_DONE, STATE_LOST):
            await update_session_state(db, session, STATE_LOST)
            lead.status = "unqualified"
        reply = reply or "No problem — feel free to reach out whenever you're ready!"
        await emit({"type": "chat_lost", "lead_id": str(lead.id), "payload": {}})

    elif classification == "question":
        if current_state == STATE_GREETING:
            await update_session_state(db, session, STATE_INTENT_CONFIRM)
        reply = reply or "Got it — let me think about that. Could you share a bit more about your business?"

    elif classification == "accept":
        if current_state == STATE_GREETING:
            await update_session_state(db, session, STATE_INTENT_CONFIRM)
            reply = reply or "Great! What kind of social media help are you looking for?"
        elif current_state == STATE_INTENT_CONFIRM:
            await update_session_state(db, session, STATE_PROPOSE_TIMES)
            slots = await generate_slots(db, [])
            session.proposed_slots = slots
            proposed_times = slots
            reply = reply or "Awesome — here are a few times I'm free. Which works best?"
        elif current_state == STATE_PROPOSE_TIMES:
            await update_session_state(db, session, STATE_CONFIRM)
            reply = reply or "Perfect, let's lock that in. Confirm that time works?"
        elif current_state == STATE_CONFIRM:
            await update_session_state(db, session, STATE_BOOK)
            slot = session.proposed_slots[0] if session.proposed_slots else None
            if slot:
                start_dt = datetime.fromisoformat(slot)
                end_dt = start_dt + timedelta(minutes=30)
                event = await insert_event(
                    summary=f"ASDR Demo - {lead.email}",
                    start_dt=start_dt,
                    end_dt=end_dt,
                    attendee_emails=[lead.email] if lead.email else [],
                )
                meeting = Meeting(
                    lead_id=lead.id,
                    source="chat",
                    google_event_id=event.get("id", ""),
                    title=f"ASDR Demo - {lead.email}",
                    start_at=start_dt,
                    end_at=end_dt,
                    hangout_link=event.get("hangoutLink"),
                    status="booked",
                )
                db.add(meeting)
                lead.status = "booked"
                await db.flush()
                await db.refresh(meeting)
                booked_meeting = MeetingOut(
                    id=meeting.id,
                    lead_id=meeting.lead_id,
                    source=meeting.source,
                    google_event_id=meeting.google_event_id,
                    title=meeting.title,
                    start_at=meeting.start_at,
                    end_at=meeting.end_at,
                    hangout_link=meeting.hangout_link,
                    status=meeting.status,
                    created_at=meeting.created_at,
                    updated_at=meeting.updated_at,
                )
            reply = reply or "All booked! You'll get a calendar invite shortly."
            await emit({
                "type": "meeting_booked",
                "lead_id": str(lead.id),
                "payload": {},
            })

    elif classification == "propose_alt":
        if current_state == STATE_PROPOSE_TIMES:
            session.retry_count = (session.retry_count or 0) + 1
            slots = await generate_slots(db, [], retry_count=session.retry_count)
            session.proposed_slots = slots
            proposed_times = slots
            reply = reply or "No worries — how about one of these instead?"

    lead.last_activity_at = datetime.now(timezone.utc)
    out_msg = await add_chat_message(db, session.id, "outbound", reply)
    await db.commit()

    await emit({
        "type": "chat_message",
        "lead_id": str(lead.id),
        "payload": {"state": session.state, "text": body.text},
    })

    return ChatMessageOut(
        reply=reply,
        state=session.state,
        proposed_times=proposed_times,
        booked_meeting=booked_meeting,
    )


@router.get("/history/{lead_id}")
async def chat_history_endpoint(lead_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ChatSession).where(ChatSession.lead_id == UUID(lead_id))
    )
    session = result.scalar_one_or_none()
    if not session:
        return {"messages": [], "state": STATE_GREETING}

    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = msg_result.scalars().all()
    return {
        "session_id": str(session.id),
        "state": session.state,
        "messages": [
            {
                "id": str(m.id),
                "direction": m.direction,
                "text": m.text,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
        "proposed_slots": session.proposed_slots or [],
    }
