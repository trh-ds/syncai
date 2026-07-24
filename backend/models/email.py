import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator
from sqlalchemy import Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Email(Base):
    __tablename__ = "emails"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    sender: Mapped[str] = mapped_column(Text, nullable=False)
    sender_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    ai_draft: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending", server_default="pending")
    gmail_message_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True, unique=True)
    gmail_thread_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Set when this email is a reply to one we sent: interested | not-now | referral | objection | unsubscribe
    reply_intent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=_utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=_utcnow, onupdate=_utcnow, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_emails_status", "status"),
        Index("ix_emails_created_at_desc", created_at.desc()),
    )


# ---------- Pydantic schemas ----------

Intent = Literal["Sales", "Support", "Spam", "Other"]
Status = Literal["pending", "approved", "discarded", "sent"]


class EmailIn(BaseModel):
    sender: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)
    gmail_message_id: Optional[str] = None
    gmail_thread_id: Optional[str] = None


class EmailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender: str
    sender_name: Optional[str]
    subject: str
    body: str
    intent: str
    summary: str
    ai_draft: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def _ser_dt(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class EmailPatch(BaseModel):
    ai_draft: Optional[str] = None
    status: Optional[Status] = None

    @model_validator(mode="after")
    def _at_least_one(self):
        if self.ai_draft is None and self.status is None:
            raise ValueError("at least one of ai_draft or status is required")
        return self


class DemoRequest(BaseModel):
    url: str = Field(min_length=1)
    sender_name: str = Field(min_length=1)
    email_body: str = Field(min_length=1)


class DemoResponse(BaseModel):
    draft: str
    context_used: str
