import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from groq import Groq
from pydantic import BaseModel, Field

from agents import rag_agent
from core.config import settings
from core.database import SessionLocal
from models.customer import Customer, Meeting
from services.calendar_service import book_event, get_availability
from services.customer_service import get_or_create_customer, log_interaction

router = APIRouter(tags=["chat"])
logger = logging.getLogger("chat")

CHAT_SYSTEM_PROMPT = """You are an expert sales assistant for {company}. You are chatting with a potential customer.

Your goals:
1. Answer their questions using the knowledge base context
2. Qualify them as a lead (hot / warm / cold)
3. If they're interested and have shared their name + email, offer to book a meeting

Lead scoring:
- hot: ready to buy, asking about pricing/booking, has clear budget
- warm: interested, asking detailed questions, not ready to commit
- cold: just browsing, vague, price shopping

When the customer wants to book a meeting, you NEED their name and email. Ask if missing.
When you have both, the system will automatically check availability and book.
Do NOT invent a booking time — just confirm you'll book and the system handles it.

Output STRICT JSON only:
{{"reply": "your chat message", "lead_score": "hot|warm|cold", "action": null}}

Knowledge base: {rag_context}
Customer context: {customer_context}
Availability (next 5 days): {availability}"""


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    email: Optional[str] = None
    name: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    lead_score: str  # hot | warm | cold
    customer_email: Optional[str] = None
    booking: Optional[dict] = None


@router.post("/chat/message", response_model=ChatResponse)
def chat_message(payload: ChatRequest):
    db = SessionLocal()
    try:
        customer = None
        if payload.email:
            customer = get_or_create_customer(db, payload.email, payload.name, source="chat")

        rag_context = rag_agent.retrieve(payload.message) or "(no knowledge base)"
        customer_context = ""
        availability_text = "Not available (calendar not connected)"
        booking_result = None

        if payload.email:
            from services.customer_service import get_customer_context
            customer_context = get_customer_context(payload.email)
            try:
                slots = get_availability(days=5)
                if slots:
                    availability_text = "\n".join(
                        f"  {s['start'][:16]} to {s['end'][11:16]} UTC"
                        for s in slots[:10]
                    )
                else:
                    availability_text = "No slots available in the next 5 days."
            except Exception as e:
                logger.warning("Availability check failed: %s", e)

        prompt = CHAT_SYSTEM_PROMPT.format(
            company=settings.CLIENT_COMPANY_NAME,
            rag_context=rag_context,
            customer_context=customer_context or "New visitor — no history.",
            availability=availability_text,
        )

        completion = Groq(api_key=settings.require_groq_key()).chat.completions.create(
            model=settings.GROQ_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": payload.message},
            ],
        )

        try:
            result = json.loads(completion.choices[0].message.content)
            reply = result.get("reply", "")
            lead_score = result.get("lead_score", "cold")
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Chat LLM parse error: %s", e)
            return ChatResponse(
                reply="I'm having trouble understanding. Could you rephrase?",
                lead_score="cold",
            )

        if customer:
            log_interaction(customer.id, "chat", payload.message, "inbound", db)
            log_interaction(customer.id, "chat", reply, "outbound", db)
            if lead_score in ("hot", "warm", "cold"):
                customer.lead_score = lead_score
            customer.name = payload.name or customer.name
            db.commit()

        customer_email = payload.email or (customer.email if customer else None)

        if _is_booking_request(payload.message) and customer and customer_email:
            try:
                booking_result = _attempt_booking(db, customer, payload.name or customer.name or "Client")
            except Exception as e:
                logger.error("Booking attempt failed: %s", e)

        return ChatResponse(
            reply=reply,
            lead_score=lead_score,
            customer_email=customer_email,
            booking=booking_result,
        )
    finally:
        db.close()


def _is_booking_request(message: str) -> bool:
    lower = message.lower()
    keywords = ["book", "schedule", "meeting", "appointment", "calendar", "call", "demo"]
    return any(k in lower for k in keywords)


def _attempt_booking(db, customer: Customer, attendee_name: str) -> dict | None:
    slots = get_availability(days=7)
    if not slots:
        return {"error": "No available slots in the next 7 days."}

    slot = slots[0]
    start = datetime.fromisoformat(slot["start"])
    end = datetime.fromisoformat(slot["end"])

    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    event = book_event(
        summary=f"Meeting with {attendee_name} ({customer.email})",
        start=start,
        end=end,
        attendee_email=customer.email,
        attendee_name=attendee_name,
    )

    if not event:
        return {"error": "Failed to create calendar event."}

    meeting = Meeting(
        customer_id=customer.id,
        google_event_id=event["id"],
        summary=event["summary"],
        start_time=start,
        end_time=end,
        status="scheduled",
    )
    db.add(meeting)
    customer.lead_score = "hot"
    db.commit()

    from services.gmail_client import GmailClient
    try:
        gmail = GmailClient()
        confirm_body = (
            f"Hi {attendee_name},\n\n"
            f"Your meeting is confirmed!\n\n"
            f"Date: {start.strftime('%A, %B %d, %Y')}\n"
            f"Time: {start.strftime('%I:%M %p')} – {end.strftime('%I:%M %p')} UTC\n\n"
            f"We look forward to speaking with you.\n\n"
            f"Best,\n{settings.CLIENT_COMPANY_NAME}"
        )
        gmail.send_reply(
            thread_id="",
            to=customer.email,
            subject="Meeting Confirmed",
            body=confirm_body,
            message_id="",
        )
    except Exception as e:
        logger.warning("Confirmation email failed: %s", e)

    return {
        "confirmed": True,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "summary": event["summary"],
    }
