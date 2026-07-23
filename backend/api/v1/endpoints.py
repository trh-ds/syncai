import re
import uuid

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException, Query
from groq import APIError as GroqAPIError
from sqlalchemy.orm import Session

from agents import draft_agent
from core.database import get_db
from models.email import DemoRequest, DemoResponse, Email, EmailOut, EmailPatch, Status

router = APIRouter(tags=["emails"])


@router.get("/emails", response_model=list[EmailOut])
def list_emails(status: Status | None = Query(default=None), db: Session = Depends(get_db)):
    q = db.query(Email)
    if status:
        q = q.filter(Email.status == status)
    return q.order_by(Email.created_at.desc()).all()


@router.get("/emails/{email_id}", response_model=EmailOut)
def get_email(email_id: uuid.UUID, db: Session = Depends(get_db)):
    record = db.get(Email, email_id)
    if not record:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Email not found"})
    return record


@router.patch("/emails/{email_id}", response_model=EmailOut)
def patch_email(email_id: uuid.UUID, patch: EmailPatch, db: Session = Depends(get_db)):
    record = db.get(Email, email_id)
    if not record:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Email not found"})
    if patch.ai_draft is not None:
        record.ai_draft = patch.ai_draft
    if patch.status is not None:
        if record.status != "pending":
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALID_TRANSITION", "message": f"Cannot change status from '{record.status}'"},
            )
        if patch.status not in ("approved", "discarded"):
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALID_STATUS", "message": f"Status must be 'approved' or 'discarded', got '{patch.status}'"},
            )
        record.status = patch.status
    db.commit()
    db.refresh(record)
    return record


def _scrape_text(url: str, max_chars: int = 4000) -> str:
    with httpx.Client(follow_redirects=True, timeout=10.0, headers={"User-Agent": "ASDR-Demo/1.0"}) as client:
        resp = client.get(url)
        resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()
    return text[:max_chars]


@router.post("/demo/run", response_model=DemoResponse)
def demo_run(payload: DemoRequest):
    try:
        context = _scrape_text(payload.url)
    except Exception as e:
        raise HTTPException(status_code=502, detail={"code": "SCRAPE_FAILED", "message": f"Failed to scrape URL: {e}"})
    try:
        draft = draft_agent.draft_reply(payload.email_body, payload.sender_name, "Public demo request", context)
    except (RuntimeError, GroqAPIError) as e:
        raise HTTPException(status_code=502, detail={"code": "LLM_ERROR", "message": str(e)})
    return DemoResponse(draft=draft, context_used=context)
