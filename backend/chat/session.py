from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import ChatSession, ChatMessage

STATE_GREETING = "GREETING"
STATE_COLLECT_INFO = "COLLECT_INFO"
STATE_INTENT_CONFIRM = "INTENT_CONFIRM"
STATE_PROPOSE_TIMES = "PROPOSE_TIMES"
STATE_CONFIRM = "CONFIRM"
STATE_BOOK = "BOOK"
STATE_DONE = "DONE"
STATE_LOST = "LOST"

STATE_TRANSITIONS: dict[str, list[str]] = {
    STATE_GREETING: [STATE_COLLECT_INFO, STATE_LOST],
    STATE_COLLECT_INFO: [STATE_INTENT_CONFIRM, STATE_LOST],
    STATE_INTENT_CONFIRM: [STATE_PROPOSE_TIMES, STATE_CONFIRM, STATE_LOST],
    STATE_PROPOSE_TIMES: [STATE_CONFIRM, STATE_PROPOSE_TIMES, STATE_LOST],
    STATE_CONFIRM: [STATE_BOOK, STATE_PROPOSE_TIMES, STATE_LOST],
    STATE_BOOK: [STATE_DONE],
    STATE_DONE: [],
    STATE_LOST: [],
}


def valid_transition(current: str, next_state: str) -> bool:
    return next_state in STATE_TRANSITIONS.get(current, [])


async def get_or_create_session(db: AsyncSession, lead_id: UUID) -> ChatSession:
    result = await db.execute(
        select(ChatSession).where(ChatSession.lead_id == lead_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        session = ChatSession(lead_id=lead_id, state=STATE_GREETING)
        db.add(session)
        await db.flush()
    return session


async def update_session_state(db: AsyncSession, session: ChatSession, new_state: str):
    session.state = new_state
    session.updated_at = datetime.now(timezone.utc)
    await db.flush()


async def add_chat_message(db: AsyncSession, session_id: UUID, direction: str, text: str) -> ChatMessage:
    msg = ChatMessage(session_id=session_id, direction=direction, text=text)
    db.add(msg)
    await db.flush()
    return msg
