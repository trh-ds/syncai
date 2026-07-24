import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.auth import get_org
from core.database import get_db
from models.customer import Customer, Interaction, Meeting
from models.email import Email
from models.org import Organization
from services.customer_service import FORECAST_WEIGHT

router = APIRouter(prefix="/crm", tags=["crm"])

SERVICE_KEYWORDS = {
    "Web Design": ["web design", "website", "redesign", "site", "landing page"],
    "SEO": ["seo", "search engine", "ranking", "traffic", "google"],
    "Marketing": ["marketing", "ads", "campaign", "social media", "branding"],
    "Development": ["development", "app", "software", "custom", "platform"],
    "Consulting": ["consulting", "strategy", "audit", "roadmap"],
    "Other": [],
}


def _classify_service(text: str) -> str:
    low = text.lower()
    for service, keywords in SERVICE_KEYWORDS.items():
        for kw in keywords:
            if kw in low:
                return service
    return "Other"


class StatsOut(BaseModel):
    total_leads: int
    hot: int
    warm: int
    cold: int
    total_meetings: int
    pipeline_value: float
    pipeline_forecast: float  # stage-weighted
    by_source: dict[str, int]
    by_service: dict[str, int]


# ponytail: simple aggregator, no ORM magic
class RecentActivity(BaseModel):
    type: str  # email | chat | meeting
    description: str
    timestamp: str


@router.get("/stats", response_model=StatsOut)
def crm_stats(org: Organization = Depends(get_org), db: Session = Depends(get_db)):
    customers = db.query(Customer).filter(Customer.org_id == org.id).all()
    lead_counts = {"hot": 0, "warm": 0, "cold": 0}
    source_counts: dict[str, int] = {}
    service_counts: dict[str, int] = {k: 0 for k in SERVICE_KEYWORDS}
    pipeline_value = 0.0
    pipeline_forecast = 0.0

    for c in customers:
        lead_counts[c.lead_score] = lead_counts.get(c.lead_score, 0) + 1
        source_counts[c.source] = source_counts.get(c.source, 0) + 1
        value = c.deal_value_estimate or 0.0
        pipeline_value += value
        pipeline_forecast += value * FORECAST_WEIGHT.get(c.lead_score, 0.05)

    # Service breakdown from email summaries
    emails = db.query(Email).filter(Email.org_id == org.id).all()
    for e in emails:
        svc = _classify_service(e.subject + " " + e.summary)
        service_counts[svc] = service_counts.get(svc, 0) + 1

    # Also classify from chat interactions
    interactions = db.query(Interaction).filter(Interaction.channel == "chat", Interaction.org_id == org.id).all()
    for i in interactions:
        svc = _classify_service(i.content)
        if svc != "Other":
            service_counts[svc] = service_counts.get(svc, 0) + 1

    meetings_count = db.query(Meeting).filter(Meeting.status == "scheduled", Meeting.org_id == org.id).count()

    return StatsOut(
        total_leads=len(customers),
        hot=lead_counts["hot"],
        warm=lead_counts["warm"],
        cold=lead_counts["cold"],
        total_meetings=meetings_count,
        pipeline_value=round(pipeline_value, 2),
        pipeline_forecast=round(pipeline_forecast, 2),
        by_source=source_counts,
        by_service={k: v for k, v in service_counts.items() if v > 0},
    )


@router.get("/activity", response_model=list[RecentActivity])
def crm_activity(limit: int = Query(default=20), org: Organization = Depends(get_org), db: Session = Depends(get_db)):
    activities: list[RecentActivity] = []

    emails = db.query(Email).filter(Email.org_id == org.id).order_by(Email.created_at.desc()).limit(limit).all()
    for e in emails:
        activities.append(RecentActivity(
            type="email",
            description=f"{e.sender_name or e.sender}: {e.summary}",
            timestamp=_fmt(e.created_at),
        ))

    interactions = (
        db.query(Interaction)
        .filter(Interaction.org_id == org.id)
        .order_by(Interaction.created_at.desc())
        .limit(limit)
        .all()
    )
    for i in interactions:
        activities.append(RecentActivity(
            type="chat",
            description=f"{i.direction}: {i.content[:100]}",
            timestamp=_fmt(i.created_at),
        ))

    meetings = (
        db.query(Meeting)
        .filter(Meeting.org_id == org.id)
        .order_by(Meeting.created_at.desc())
        .limit(limit)
        .all()
    )
    for m in meetings:
        activities.append(RecentActivity(
            type="meeting",
            description=f"{m.summary} ({m.status})",
            timestamp=_fmt(m.created_at),
        ))

    activities.sort(key=lambda a: a.timestamp, reverse=True)
    return activities[:limit]


def _fmt(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
