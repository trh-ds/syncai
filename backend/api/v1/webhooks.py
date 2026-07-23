from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from groq import APIError as GroqAPIError
from sqlalchemy.orm import Session

from agents import draft_agent, rag_agent, triage_agent
from core.database import get_db
from models.email import Email, EmailIn, EmailOut
from services.lead_filter import is_potential_lead

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/email", status_code=201, response_model=EmailOut)
def receive_email(payload: EmailIn, db: Session = Depends(get_db)):
    # Pre-filter: skip LLM for obvious non-leads
    if not is_potential_lead(payload.sender, payload.subject):
        record = Email(
            sender=payload.sender,
            sender_name=None,
            subject=payload.subject,
            body=payload.body,
            intent="Other",
            summary="Automated/system email — no draft needed",
            ai_draft=None,
            status="pending",
            gmail_message_id=payload.gmail_message_id,
            gmail_thread_id=payload.gmail_thread_id,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    try:
        triage = triage_agent.triage(payload.sender, payload.subject, payload.body)
        ai_draft = None
        if triage.should_draft and triage.intent in ("Sales", "Support"):
            context = rag_agent.retrieve(f"{payload.subject}\n{payload.body}")
            ai_draft = draft_agent.draft_reply(payload.body, triage.sender_name, triage.summary, context)
    except (RuntimeError, GroqAPIError) as e:
        return JSONResponse(status_code=502, content={"error": {"code": "LLM_ERROR", "message": str(e)}})

    record = Email(
        sender=payload.sender,
        sender_name=triage.sender_name,
        subject=payload.subject,
        body=payload.body,
        intent=triage.intent,
        summary=triage.summary,
        ai_draft=ai_draft,
        status="pending",
        gmail_message_id=payload.gmail_message_id,
        gmail_thread_id=payload.gmail_thread_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
