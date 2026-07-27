from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.session import get_db
from models import Lead, EmailMessage, ChatMessage, Meeting, ActivityEvent, EmailThread, ChatSession
from schemas import LeadOut, LeadTimelineOut, LeadTimelineEvent
from apollo.client import sync_apollo_leads

router = APIRouter(prefix="/api/leads", tags=["leads"])

_sync_status: dict = {"running": False, "count": 0, "error": None}


def _lead_to_out(lead: Lead) -> LeadOut:
    return LeadOut(
        id=lead.id,
        org_id=lead.org_id,
        first_name=lead.first_name,
        last_name=lead.last_name,
        email=lead.email,
        title=lead.title,
        linkedin_url=lead.linkedin_url,
        source=lead.source,
        status=lead.status,
        apollo_person_id=lead.apollo_person_id,
        enriched_data=lead.enriched_data,
        org_name=lead.organization.name if lead.organization else None,
        org_industry=lead.organization.industry if lead.organization else None,
        org_employee_count=lead.organization.employee_count if lead.organization else None,
        last_activity_at=lead.last_activity_at,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


@router.get("/", response_model=list[LeadOut])
async def list_leads(
    search: str = "",
    source: str = "",
    status: str = "",
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    query = select(Lead).options(selectinload(Lead.organization))

    if search:
        pattern = f"%{search}%"
        query = query.where(
            (Lead.email.ilike(pattern))
            | (Lead.first_name.ilike(pattern))
            | (Lead.last_name.ilike(pattern))
        )
    if source:
        query = query.where(Lead.source == source)
    if status:
        query = query.where(Lead.status == status)

    query = query.order_by(Lead.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    leads = result.scalars().all()
    return [_lead_to_out(l) for l in leads]


@router.get("/{lead_id}", response_model=LeadOut)
async def get_lead(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Lead).options(selectinload(Lead.organization)).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _lead_to_out(lead)


@router.get("/{lead_id}/timeline", response_model=LeadTimelineOut)
async def get_lead_timeline(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Lead).options(
            selectinload(Lead.organization),
            selectinload(Lead.threads).selectinload(EmailThread.messages),
            selectinload(Lead.meetings),
        ).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    events: list[LeadTimelineEvent] = []

    for thread in lead.threads or []:
        for msg in thread.messages or []:
            events.append(LeadTimelineEvent(
                type=f"email_{msg.direction}",
                created_at=msg.created_at,
                payload={
                    "subject": msg.subject,
                    "body_text": msg.body_text,
                    "from_email": msg.from_email,
                    "intent": msg.intent,
                },
            ))

    for meeting in lead.meetings or []:
        events.append(LeadTimelineEvent(
            type="meeting",
            created_at=meeting.created_at,
            payload={
                "title": meeting.title,
                "start_at": meeting.start_at.isoformat() if meeting.start_at else None,
                "status": meeting.status,
                "hangout_link": meeting.hangout_link,
            },
        ))

    chat_session_result = await db.execute(
        select(ChatSession).where(ChatSession.lead_id == lead_id)
    )
    chat_session = chat_session_result.scalar_one_or_none()
    chat_sessions_list = []
    chat_messages_list = []
    if chat_session:
        chat_sessions_list = [{"id": str(chat_session.id), "state": chat_session.state}]
        msg_result = await db.execute(
            select(ChatMessage).where(ChatMessage.session_id == chat_session.id).order_by(ChatMessage.created_at.asc())
        )
        for cm in msg_result.scalars().all():
            chat_messages_list.append({"direction": cm.direction, "text": cm.text})
            events.append(LeadTimelineEvent(
                type=f"chat_{cm.direction}",
                created_at=cm.created_at,
                payload={"text": cm.text},
            ))

    act_result = await db.execute(
        select(ActivityEvent).where(ActivityEvent.lead_id == lead_id).order_by(ActivityEvent.created_at.desc())
    )
    for ae in act_result.scalars().all():
        events.append(LeadTimelineEvent(
            type=ae.type,
            created_at=ae.created_at,
            payload=ae.payload,
        ))

    events.sort(key=lambda e: e.created_at)

    return LeadTimelineOut(
        lead=_lead_to_out(lead),
        events=events,
        threads=[{
            "id": str(t.id),
            "subject": t.subject,
            "status": t.status,
            "messages": [{
                "id": str(m.id),
                "direction": m.direction,
                "from_email": m.from_email,
                "body_text": m.body_text,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            } for m in (t.messages or [])],
        } for t in (lead.threads or [])],
        meetings=[{
            "id": str(m.id),
            "title": m.title,
            "start_at": m.start_at.isoformat() if m.start_at else None,
            "status": m.status,
            "hangout_link": m.hangout_link,
        } for m in (lead.meetings or [])],
        chat_sessions=chat_sessions_list,
    )


@router.post("/sync-apollo")
async def sync_apollo(background_tasks: BackgroundTasks):
    async def _run():
        _sync_status["running"] = True
        _sync_status["error"] = None
        try:
            from db.session import async_session
            async with async_session() as db:
                count = await sync_apollo_leads(db)
                _sync_status["count"] = count
        except Exception as e:
            _sync_status["error"] = str(e)
        finally:
            _sync_status["running"] = False

    if _sync_status["running"]:
        return {"status": "already_running"}
    background_tasks.add_task(_run)
    return {"status": "started"}


@router.get("/sync-apollo/status")
async def sync_apollo_status():
    return _sync_status
