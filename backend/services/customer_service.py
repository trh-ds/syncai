from sqlalchemy.orm import Session

from models.customer import Customer, Interaction
from core.database import SessionLocal


def upsert_customer(email: str, name: str | None = None, source: str = "email") -> Customer:
    db: Session = SessionLocal()
    try:
        c = db.query(Customer).filter(Customer.email == email).first()
        if c:
            if name and not c.name:
                c.name = name
            db.commit()
            return c
        c = Customer(email=email, name=name, source=source, lead_score="cold")
        db.add(c)
        db.commit()
        db.refresh(c)
        return c
    finally:
        db.close()


def get_or_create_customer(db: Session, email: str, name: str | None = None, source: str = "email") -> Customer:
    c = db.query(Customer).filter(Customer.email == email).first()
    if c:
        if name and not c.name:
            c.name = name
        return c
    c = Customer(email=email, name=name, source=source, lead_score="cold")
    db.add(c)
    return c


def log_interaction(
    customer_id: str, channel: str, content: str, direction: str, db: Session | None = None
) -> Interaction:
    close = False
    if db is None:
        db = SessionLocal()
        close = True
    try:
        i = Interaction(customer_id=customer_id, channel=channel, content=content, direction=direction)
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
