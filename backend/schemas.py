from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


# --- Lead ---
class LeadBase(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    title: str | None = None
    linkedin_url: str | None = None
    source: str | None = None
    status: str | None = None
    apollo_person_id: str | None = None
    enriched_data: dict | None = None
    org_name: str | None = None
    org_industry: str | None = None
    org_employee_count: int | None = None


class LeadOut(LeadBase):
    id: UUID
    org_id: UUID | None = None
    last_activity_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadTimelineEvent(BaseModel):
    type: str
    created_at: datetime
    payload: dict | None = None


class LeadTimelineOut(BaseModel):
    lead: LeadOut
    events: list[LeadTimelineEvent]
    threads: list = []
    meetings: list = []
    chat_sessions: list = []


# --- Meeting ---
class MeetingBookIn(BaseModel):
    lead_id: UUID
    title: str
    start_at: datetime
    end_at: datetime
    source: str = "manual"


class MeetingOut(BaseModel):
    id: UUID
    lead_id: UUID | None = None
    source: str | None = None
    google_event_id: str | None = None
    title: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    hangout_link: str | None = None
    status: str | None = None
    created_at: datetime
    updated_at: datetime
    lead_name: str | None = None
    lead_email: str | None = None

    model_config = {"from_attributes": True}


# --- Chat ---
class ChatMessageIn(BaseModel):
    lead_id: str
    text: str


class ChatMessageOut(BaseModel):
    reply: str
    state: str
    proposed_times: list[str] | None = None
    booked_meeting: MeetingOut | None = None


# --- Activity ---
class ActivityEventOut(BaseModel):
    id: int
    type: str
    lead_id: UUID | None = None
    payload: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Metrics ---
class MetricsOut(BaseModel):
    leads_captured: int
    meetings_booked: int
    meetings_booked_pct: float
    est_cost_saved: float
    est_hours_saved: float
    avg_reply_latency_s: float
    pipeline: dict[str, int]
    activity_14d: list[dict]


# --- Email (for activity display) ---
class EmailSummary(BaseModel):
    message_id: str
    gmail_message_id: str
    thread_id: str | None = None
    direction: str
    from_email: str
    to_email: str
    subject: str
    body_text: str | None = None
    intent: str | None = None
    reply_latency_ms: int | None = None
    arrived_at: datetime | None = None
    sent_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
