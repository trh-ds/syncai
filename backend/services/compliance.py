"""CAN-SPAM compliance: disclosure footer, unsubscribe handling, send audit log."""

import logging
import uuid

from sqlalchemy.orm import Session

from core.config import settings
from models.customer import Customer
from models.org import SendLog

logger = logging.getLogger("compliance")


def build_footer(customer: Customer) -> str:
    """The disclosure text appended to every AI-drafted outbound email."""
    return (
        f"\n\n—\n{settings.BUSINESS_NAME}\n{settings.BUSINESS_ADDRESS}\n"
        f"You're receiving this because you contacted us. "
        f"Unsubscribe instantly: {settings.PUBLIC_API_URL}/api/v1/unsubscribe/{customer.unsubscribe_token}"
    )


def opt_out(db: Session, token: str) -> Customer | None:
    """Flip opted_out for the customer owning this token. Returns the customer."""
    customer = db.query(Customer).filter(Customer.unsubscribe_token == token).first()
    if not customer:
        return None
    if not customer.opted_out:
        customer.opted_out = True
        db.commit()
        logger.info("Customer %s opted out", customer.email)
    return customer


def can_send(customer: Customer | None) -> bool:
    """Hard gate: never send to an opted-out customer. No exceptions."""
    return customer is None or not customer.opted_out


def log_send(db: Session, recipient: str, disclosure_text: str, org_id: uuid.UUID | None = None) -> None:
    """Audit trail: exact disclosure text + timestamp for every send."""
    db.add(SendLog(org_id=org_id, recipient=recipient, disclosure_text=disclosure_text))
    db.commit()
