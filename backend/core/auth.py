"""Supabase Auth (JWT) → org resolution.

Every request resolves to an org. If no Bearer token is present (or Supabase
isn't configured), the request falls back to the default single-tenant org so
the existing demo endpoints keep working unchanged.
"""

import logging
import uuid

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core.config import settings
from core.database import default_org_id, get_db
from models.org import PLANS, Organization

logger = logging.getLogger("auth")


def _decode_supabase_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as e:
        logger.warning("JWT decode failed: %s", e)
        return None


def get_or_create_org_for_user(db: Session, user_id: str, email: str | None) -> Organization:
    uid = uuid.UUID(user_id)
    org = db.query(Organization).filter(Organization.owner_user_id == uid).first()
    if org:
        return org
    org = Organization(
        name=(email.split("@")[0] + "'s org") if email else "New org",
        owner_user_id=uid,
        owner_email=email,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def get_org(request: Request, db: Session = Depends(get_db)) -> Organization:
    """Resolve the caller's org. Falls back to the default org when unauthenticated."""
    auth = request.headers.get("authorization", "")
    if settings.SUPABASE_JWT_SECRET and auth.startswith("Bearer "):
        claims = _decode_supabase_token(auth[7:])
        if claims and claims.get("sub"):
            return get_or_create_org_for_user(db, claims["sub"], claims.get("email"))
        raise HTTPException(status_code=401, detail={"code": "INVALID_TOKEN", "message": "Invalid or expired token"})
    org_id = default_org_id(db)
    org = db.get(Organization, org_id) if org_id else None
    if not org:
        raise HTTPException(status_code=500, detail={"code": "NO_ORG", "message": "No organization configured"})
    return org


def require_auth(org: Organization = Depends(get_org)) -> Organization:
    """Like get_org but rejects unauthenticated (default-org) fallback."""
    if org.owner_user_id is None and settings.SUPABASE_JWT_SECRET:
        raise HTTPException(status_code=401, detail={"code": "AUTH_REQUIRED", "message": "Sign in required"})
    return org


def require_plan(min_plan: str):
    """Server-side plan gate. Usage: Depends(require_plan('growth'))."""
    min_rank = PLANS.index(min_plan)

    def _dep(org: Organization = Depends(get_org)) -> Organization:
        rank = PLANS.index(org.plan) if org.plan in PLANS else 0
        if rank < min_rank:
            raise HTTPException(
                status_code=402,
                detail={"code": "PLAN_REQUIRED", "message": f"This feature requires the {min_plan} plan or higher"},
            )
        return org

    return _dep
