from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from events import emit
from models import Lead, ChatSession, ChatMessage, Meeting
from schemas import ChatMessageIn, ChatMessageOut, MeetingOut
from chat.session import (
    get_or_create_session,
    update_session_state,
    add_chat_message,
    STATE_GREETING,
    STATE_COLLECT_INFO,
    STATE_INTENT_CONFIRM,
    STATE_PROPOSE_TIMES,
    STATE_CONFIRM,
    STATE_BOOK,
    STATE_DONE,
    STATE_LOST,
)
from chat.llm_turn import process_turn
from chat.slots import generate_slots, is_slot_available

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/message", response_model=ChatMessageOut)
async def chat_message(body: ChatMessageIn, db: AsyncSession = Depends(get_db)):
    lead = None
    try:
        lead = await db.get(Lead, UUID(body.lead_id))
    except (ValueError, Exception):
        pass
    if not lead:
        chat_email = f"chat-{body.lead_id}@unknown.com"
        result = await db.execute(select(Lead).where(Lead.email == chat_email))
        lead = result.scalar_one_or_none()
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

    # --- Extract contact info ---
    name = (turn.get("name") or "").strip()
    company = (turn.get("company") or "").strip()
    email = (turn.get("email") or "").strip()

    if name and not lead.first_name:
        parts = name.split(maxsplit=1)
        lead.first_name = parts[0]
        lead.last_name = parts[1] if len(parts) > 1 else ""
    if company and not lead.title:
        lead.title = company  # ponytail: store company in title until we add a real field
    if email and "@" in email and lead.email.startswith("chat-"):
        lead.email = email

    # --- Check for requested datetime ---
    requested_dt_str = (turn.get("requested_datetime") or "").strip()

    # --- State machine ---
    if classification == "decline" or current_state in (STATE_DONE, STATE_LOST):
        if current_state not in (STATE_DONE, STATE_LOST):
            await update_session_state(db, session, STATE_LOST)
            lead.status = "lost"
        reply = reply or "No problem — feel free to reach out whenever you're ready!"
        await emit({"type": "chat_lost", "lead_id": str(lead.id), "payload": {}})

    elif classification == "question":
        if current_state == STATE_GREETING:
            reply = reply or "Hello! Who do I have the pleasure of speaking with? What's your name and company?"
        else:
            reply = reply or "Sure — tell me a bit more and I'll help."

    elif classification == "accept":
        if current_state == STATE_GREETING:
            await update_session_state(db, session, STATE_COLLECT_INFO)
            reply = reply or "Great to meet you! I'm Maya from SocialBoost. To get started, could you share your name, company, and email?"

        elif current_state == STATE_COLLECT_INFO:
            has_name = bool(name or lead.first_name)
            has_company = bool(company or lead.title)
            has_email = bool((email and "@" in email) or (lead.email and not lead.email.startswith("chat-")))

            if has_name and has_company and has_email:
                await update_session_state(db, session, STATE_INTENT_CONFIRM)
                reply = reply or f"Thanks {lead.first_name or name}! What kind of branding help are you looking for?"
            else:
                reply = reply or "Almost there — I still need your name, company, and email to get you set up properly."

        elif current_state == STATE_INTENT_CONFIRM:
            if requested_dt_str:
                try:
                    req_dt = datetime.fromisoformat(requested_dt_str)
                    if req_dt.tzinfo is None:
                        req_dt = req_dt.replace(tzinfo=timezone.utc)

                    meeting_result = await db.execute(
                        select(Meeting).where(Meeting.status.notin_(["cancelled"]))
                    )
                    existing = list(meeting_result.scalars().all())

                    if await is_slot_available(db, req_dt, existing):
                        session.proposed_slots = [req_dt.isoformat()]
                        await update_session_state(db, session, STATE_CONFIRM)
                        reply = reply or f"{req_dt.strftime('%B %d at %I:%M %p')} works perfectly! Shall I lock it in?"
                    else:
                        session.retry_count = 1
                        slots = await generate_slots(db, existing, retry_count=1)
                        session.proposed_slots = slots
                        proposed_times = slots
                        await update_session_state(db, session, STATE_PROPOSE_TIMES)
                        reply = reply or f"That time isn't available, but here are some open slots that work:"
                except (ValueError, Exception):
                    await update_session_state(db, session, STATE_PROPOSE_TIMES)
                    meeting_result = await db.execute(
                        select(Meeting).where(Meeting.status.notin_(["cancelled"]))
                    )
                    existing = list(meeting_result.scalars().all())
                    slots = await generate_slots(db, existing)
                    session.proposed_slots = slots
                    proposed_times = slots
                    reply = reply or "Here are a few times I'm free — which works best?"
            else:
                await update_session_state(db, session, STATE_PROPOSE_TIMES)
                meeting_result = await db.execute(
                    select(Meeting).where(Meeting.status.notin_(["cancelled"]))
                )
                existing = list(meeting_result.scalars().all())
                slots = await generate_slots(db, existing)
                session.proposed_slots = slots
                proposed_times = slots
                reply = reply or "Here are a few times I'm free — which works best?"

        elif current_state == STATE_PROPOSE_TIMES:
            await update_session_state(db, session, STATE_CONFIRM)
            reply = reply or "Perfect, let's lock that in. Confirm that time works?"

        elif current_state == STATE_CONFIRM:
            await update_session_state(db, session, STATE_BOOK)
            slot = session.proposed_slots[0] if session.proposed_slots else None
            if slot:
                start_dt = datetime.fromisoformat(slot)
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                end_dt = start_dt + timedelta(minutes=30)
                meeting = Meeting(
                    lead_id=lead.id,
                    source="chat",
                    title=f"Branding Consult — {lead.first_name or 'Prospect'}",
                    start_at=start_dt,
                    end_at=end_dt,
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
            reply = reply or "All booked! Looking forward to our call."
            await emit({
                "type": "meeting_booked",
                "lead_id": str(lead.id),
                "payload": {},
            })

    elif classification == "propose_alt":
        if current_state == STATE_PROPOSE_TIMES:
            session.retry_count = (session.retry_count or 0) + 1
            meeting_result = await db.execute(
                select(Meeting).where(Meeting.status.notin_(["cancelled"]))
            )
            existing = list(meeting_result.scalars().all())
            slots = await generate_slots(db, existing, retry_count=session.retry_count)
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
