"""Self-serve Gmail + Calendar connection — replaces the manual scripts/gmail_auth.py run."""

import logging
import uuid
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import require_auth
from core.config import settings
from core.database import get_db
from models.org import Organization

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
logger = logging.getLogger("onboarding")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
]


class ConnectUrlOut(BaseModel):
    auth_url: str


class StatusOut(BaseModel):
    gmail_connected: bool
    gmail_user: str | None
    plan: str


@router.get("/status", response_model=StatusOut)
def status(org: Organization = Depends(require_auth)):
    return StatusOut(
        gmail_connected=bool(org.gmail_refresh_token),
        gmail_user=org.gmail_user_email,
        plan=org.plan,
    )


@router.get("/google", response_model=ConnectUrlOut)
def google_connect(org: Organization = Depends(require_auth)):
    if not (settings.GMAIL_CLIENT_ID and settings.GMAIL_CLIENT_SECRET):
        raise HTTPException(status_code=503, detail={"code": "OAUTH_DISABLED", "message": "Google OAuth not configured"})
    # ponytail: state = org id — fine for MVP; sign it if org ids become guessable targets
    params = {
        "client_id": settings.GMAIL_CLIENT_ID,
        "redirect_uri": f"{settings.PUBLIC_API_URL}/api/v1/onboarding/google/callback",
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": str(org.id),
    }
    return ConnectUrlOut(auth_url=f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}")


@router.get("/google/callback")
def google_callback(code: str = Query(...), state: str = Query(...), db: Session = Depends(get_db)):
    org = db.get(Organization, uuid.UUID(state))
    if not org:
        raise HTTPException(status_code=400, detail={"code": "BAD_STATE", "message": "Unknown org"})

    token_resp = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "redirect_uri": f"{settings.PUBLIC_API_URL}/api/v1/onboarding/google/callback",
            "grant_type": "authorization_code",
        },
        timeout=15.0,
    )
    if token_resp.status_code != 200:
        logger.error("Token exchange failed: %s", token_resp.text)
        raise HTTPException(status_code=502, detail={"code": "TOKEN_EXCHANGE_FAILED", "message": "Google token exchange failed"})
    tokens = token_resp.json()

    # Gmail profile → connected email address
    profile = httpx.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/profile",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        timeout=10.0,
    )
    email = profile.json().get("emailAddress") if profile.status_code == 200 else None

    org.gmail_refresh_token = tokens.get("refresh_token", org.gmail_refresh_token)
    org.gmail_user_email = email
    db.commit()
    logger.info("Org %s connected Gmail %s", org.id, email)

    return RedirectResponse(f"{settings.WEB_URL}/onboarding?connected=1")
