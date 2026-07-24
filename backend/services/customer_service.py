from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.customer import Customer, Interaction
from core.database import SessionLocal

# ponytail: flat stage heuristic — replace with per-service pricing when real deal data exists
DEAL_VALUE_BY_SCORE = {"hot": 5000.0, "warm": 2000.0, "cold": 500.0}
# Stage-weighted forecast multipliers
FORECAST_WEIGHT = {"hot": 0.7, "warm": 0.3, "cold": 0.05}


def estimate_deal_value(lead_score: str) -> float:
    return DEAL_VALUE_BY_SCORE.get(lead_score, 500.0)


def set_lead_score(c: Customer, score: str) -> None:
    if score in DEAL_VALUE_BY_SCORE:
        c.lead_score = score
        c.deal_value_estimate = estimate_deal_value(score)


def _new_customer(email: str, name: str | None, source: str, org_id=None) -> Customer:
    return Customer(
        email=email,
        name=name,
        source=source,
        lead_score="cold",
        org_id=org_id,
        consent_source="inbound_email" if source == "email" else source,
        consent_timestamp=datetime.now(timezone.utc),
        deal_value_estimate=estimate_deal_value("cold"),
    )


def upsert_customer(email: str, name: str | None = None, source: str = "email", org_id=None) -> Customer:
    db: Session = SessionLocal()
    try:
        c = db.query(Customer).filter(Customer.email == email).first()
        if c:
            if name and not c.name:
                c.name = name
            if org_id and not c.org_id:
                c.org_id = org_id
            db.commit()
            return c
        c = _new_customer(email, name, source, org_id)
        db.add(c)
        db.commit()
        db.refresh(c)
        return c
    finally:
        db.close()


def get_or_create_customer(db: Session, email: str, name: str | None = None, source: str = "email", org_id=None) -> Customer:
    c = db.query(Customer).filter(Customer.email == email).first()
    if c:
        if name and not c.name:
            c.name = name
        if org_id and not c.org_id:
            c.org_id = org_id
        return c
    c = _new_customer(email, name, source, org_id)
    db.add(c)
    return c


def log_interaction(
    customer_id: str, channel: str, content: str, direction: str, db: Session | None = None, org_id=None
) -> Interaction:
    close = False
    if db is None:
        db = SessionLocal()
        close = True
    try:
        i = Interaction(customer_id=customer_id, channel=channel, content=content, direction=direction, org_id=org_id)
        db.add(i)
        db.commit()
        return i
    finally:
        if close:
            db.close()


def update_lead_score(email: str, score: str) -> Customer | None:
    db: Session = SessionLocal()
    try:
        c = db.query(Customer).filter(Customer.email == email).first()
        if c:
            c.lead_score = score
            db.commit()
    finally:
        db.close()


def get_customer_context(email: str) -> str:
    """Return recent interaction history as a text summary for LLM context."""
    db: Session = SessionLocal()
    try:
        c = db.query(Customer).filter(Customer.email == email).first()
        if not c:
            return ""
        interactions = (
            db.query(Interaction)
            .filter(Interaction.customer_id == c.id)
            .order_by(Interaction.created_at.desc())
            .limit(10)
            .all()
        )
        if not interactions:
            return f"New lead: {c.name or email}, source: {c.source}, current score: {c.lead_score}"
        history = "\n".join(
            f"[{i.channel}] {i.direction}: {i.content[:200]}"
            for i in reversed(interactions)
        )
        return (
            f"Customer: {c.name or email}\nLead score: {c.lead_score}\nSource: {c.source}\n"
            f"Recent history:\n{history}"
        )
    finally:
        db.close()
