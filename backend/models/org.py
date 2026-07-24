import uuid
from datetime import datetime, timezone

from sqlalchemy import Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Organization(Base):
    """One tenant. Multi-tenant-lite: one owner (Supabase user) per org."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, unique=True)  # Supabase auth user
    owner_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Gmail/Calendar connection (set during onboarding OAuth)
    gmail_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    gmail_user_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=_utcnow, server_default=func.now())

    __table_args__ = (Index("ix_organizations_owner_user_id", "owner_user_id"),)


class SendLog(Base):
    """CAN-SPAM audit trail: exact disclosure text + timestamp for every send."""

    __tablename__ = "send_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    recipient: Mapped[str] = mapped_column(Text, nullable=False)
    disclosure_text: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(nullable=False, default=_utcnow, server_default=func.now())

    __table_args__ = (Index("ix_send_logs_org_id", "org_id"),)
