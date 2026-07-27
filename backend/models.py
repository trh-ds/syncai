import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, DateTime, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _uuid():
    return uuid.uuid4()


def _now():
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name = Column(String)
    external_id = Column(String)
    industry = Column(String)
    employee_count = Column(Integer)


class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True)
    title = Column(String)
    linkedin_url = Column(String)
    source = Column(String)
    status = Column(String, default="captured")
    apollo_person_id = Column(String)
    enriched_data = Column(JSONB)
    last_activity_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    organization = relationship("Organization", lazy="selectin")
    threads = relationship("EmailThread", back_populates="lead", lazy="selectin")
    meetings = relationship("Meeting", back_populates="lead", lazy="selectin")


class EmailThread(Base):
    __tablename__ = "email_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    gmail_thread_id = Column(String, unique=True)
    subject = Column(String)
    status = Column(String)

    lead = relationship("Lead", back_populates="threads")
    messages = relationship("EmailMessage", back_populates="thread", lazy="selectin")


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("email_threads.id"), nullable=True)
    gmail_message_id = Column(String, unique=True)
    direction = Column(String)
    from_email = Column(String)
    to_email = Column(String)
    subject = Column(String)
    body_text = Column(Text)
    intent = Column(String)
    intent_confidence = Column(Float)
    reply_latency_ms = Column(Integer)
    arrived_at = Column(DateTime(timezone=True))
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=_now)

    thread = relationship("EmailThread", back_populates="messages")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    state = Column(String, default="GREETING")
    proposed_slots = Column(JSONB)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=True)
    direction = Column(String)
    text = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_now)


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    source = Column(String)
    google_event_id = Column(String, unique=True)
    title = Column(String)
    start_at = Column(DateTime(timezone=True))
    end_at = Column(DateTime(timezone=True))
    hangout_link = Column(String)
    status = Column(String, default="booked")
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    lead = relationship("Lead", back_populates="meetings")


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    type = Column(String)
    lead_id = Column(UUID(as_uuid=True), nullable=True)
    payload = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=_now)


class KV(Base):
    __tablename__ = "kv"

    key = Column(String, primary_key=True)
    value = Column(Text)


class DemoMetricsCache(Base):
    __tablename__ = "demo_metrics_cache"

    id = Column(Integer, primary_key=True, default=1)
    leads_count = Column(Integer, default=0)
    meetings_count = Column(Integer, default=0)
    est_cost_saved = Column(Float, default=0)
    est_hours_saved = Column(Float, default=0)
    avg_reply_latency_ms = Column(Integer, default=0)
    success_rate = Column(Float, default=0)
