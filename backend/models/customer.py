import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Float, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("organizations.id"), nullable=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_score: Mapped[str] = mapped_column(Text, nullable=False, default="cold")
    source: Mapped[str] = mapped_column(Text, nullable=False, default="email")  # email | chat
    # CAN-SPAM consent tracking
    consent_source: Mapped[str | None] = mapped_column(Text, nullable=True)  # inbound_email | chat | referral
    consent_timestamp: Mapped[datetime | None] = mapped_column(nullable=True)
    opted_out: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    unsubscribe_token: Mapped[str] = mapped_column(Text, nullable=False, default=lambda: secrets.token_urlsafe(16), unique=True)
    # Pipeline value (stage-weighted forecast input)
    deal_value_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Apollo enrichment (light per-lead lookup)
    job_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_size: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=_utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=_utcnow, onupdate=_utcnow, server_default=func.now()
    )

    interactions: Mapped[list["Interaction"]] = relationship(back_populates="customer", lazy="selectin")
    meetings: Mapped[list["Meeting"]] = relationship(back_populates="customer", lazy="selectin")

    __table_args__ = (Index("ix_customers_email", "email"), Index("ix_customers_lead_score", "lead_score"))


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("organizations.id"), nullable=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("customers.id"), nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)  # email | chat
    content: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False)  # inbound | outbound
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=_utcnow, server_default=func.now())

    customer: Mapped["Customer"] = relationship(back_populates="interactions")

    __table_args__ = (Index("ix_interactions_customer_id", "customer_id"), Index("ix_interactions_created_at_desc", created_at.desc()))


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("organizations.id"), nullable=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("customers.id"), nullable=True)
    google_event_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    start_time: Mapped[datetime] = mapped_column(nullable=False)
    end_time: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="scheduled")  # scheduled | cancelled
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=_utcnow, server_default=func.now())

    customer: Mapped["Customer | None"] = relationship(back_populates="meetings")

    __table_args__ = (Index("ix_meetings_customer_id", "customer_id"), Index("ix_meetings_start_time", "start_time"))
