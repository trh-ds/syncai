"""Stripe billing — Checkout (test mode) + webhook. Raw HTTP via httpx; no SDK needed."""

import hashlib
import hmac
import json
import logging
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.auth import get_org, require_auth
from core.config import settings
from core.database import get_db
from models.org import PLANS, Organization

router = APIRouter(prefix="/billing", tags=["billing"])
logger = logging.getLogger("billing")

STRIPE_API = "https://api.stripe.com/v1"


def _price_for(plan: str) -> str:
    return {
        "starter": settings.STRIPE_PRICE_STARTER,
        "growth": settings.STRIPE_PRICE_GROWTH,
        "scale": settings.STRIPE_PRICE_SCALE,
    }.get(plan, "")


class CheckoutRequest(BaseModel):
    plan: str = Field(pattern="^(starter|growth|scale)$")


class CheckoutResponse(BaseModel):
    checkout_url: str


class PlanOut(BaseModel):
    plan: str
    stripe_configured: bool


@router.get("/plan", response_model=PlanOut)
def get_plan(org: Organization = Depends(get_org)):
    return PlanOut(plan=org.plan, stripe_configured=bool(settings.STRIPE_SECRET_KEY))


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(payload: CheckoutRequest, org: Organization = Depends(require_auth)):
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail={"code": "BILLING_DISABLED", "message": "Stripe is not configured"})
    price = _price_for(payload.plan)
    if not price:
        raise HTTPException(status_code=503, detail={"code": "PRICE_MISSING", "message": f"No Stripe price configured for {payload.plan}"})

    resp = httpx.post(
        f"{STRIPE_API}/checkout/sessions",
        auth=(settings.STRIPE_SECRET_KEY, ""),
        data={
            "mode": "subscription",
            "line_items[0][price]": price,
            "line_items[0][quantity]": "1",
            "success_url": f"{settings.WEB_URL}/onboarding?billing=success",
            "cancel_url": f"{settings.WEB_URL}/#pricing",
            "client_reference_id": str(org.id),
            "metadata[plan]": payload.plan,
        },
        timeout=15.0,
    )
    if resp.status_code != 200:
        logger.error("Stripe checkout failed: %s", resp.text)
        raise HTTPException(status_code=502, detail={"code": "STRIPE_ERROR", "message": resp.json().get("error", {}).get("message", "Stripe error")})
    return CheckoutResponse(checkout_url=resp.json()["url"])


def _verify_stripe_signature(raw_body: bytes, header: str) -> bool:
    """Manual Stripe webhook signature check (stdlib hmac)."""
    try:
        parts = dict(p.split("=", 1) for p in header.split(","))
        expected = hmac.new(
            settings.STRIPE_WEBHOOK_SECRET.encode(),
            f"{parts['t']}.{raw_body.decode()}".encode(),
            hashlib.sha256,
        ).hexdigest()
        if abs(time.time() - int(parts["t"])) > 300:
            return False
        return hmac.compare_digest(expected, parts["v1"])
    except Exception:
        return False


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    raw = await request.body()
    sig = request.headers.get("stripe-signature", "")
    if not settings.STRIPE_WEBHOOK_SECRET or not _verify_stripe_signature(raw, sig):
        raise HTTPException(status_code=400, detail={"code": "BAD_SIGNATURE", "message": "Invalid webhook signature"})

    event = json.loads(raw)
    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        org_id = session.get("client_reference_id")
        plan = (session.get("metadata") or {}).get("plan", "starter")
        if org_id and plan in PLANS:
            import uuid as _uuid

            org = db.get(Organization, _uuid.UUID(org_id))
            if org:
                org.plan = plan
                org.stripe_customer_id = session.get("customer")
                db.commit()
                logger.info("Org %s upgraded to %s", org_id, plan)
    return {"received": True}
