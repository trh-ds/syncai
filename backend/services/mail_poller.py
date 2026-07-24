import asyncio
import base64
import logging
import re
from email.header import decode_header

from googleapiclient.errors import HttpError
from groq import APIError as GroqAPIError
from sqlalchemy.orm import Session

from agents import draft_agent, enrichment_agent, rag_agent, triage_agent
from core.config import settings
from core.database import SessionLocal
from models.customer import Customer
from models.email import Email
from models.org import Organization
from services import compliance, slack_notify
from services.customer_service import log_interaction, set_lead_score, upsert_customer
from services.gmail_client import GmailClient
from services.lead_filter import is_potential_lead

logger = logging.getLogger("mail_poller")

SENDER_RE = re.compile(r"<?([^@\s]+@[^@\s>]+)")


def _decode_header(value: str) -> str:
    parts = decode_header(value)
    decoded = []
    for text, charset in parts:
        if isinstance(text, bytes):
            decoded.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(str(text))
    return " ".join(decoded)


def _extract_email(raw: str) -> str:
    m = SENDER_RE.search(raw)
    return m.group(1) if m else raw.strip()


def _parse_payload(msg: dict) -> tuple[str, str, str]:
    """Return (sender_email, subject, body) from a full-format Gmail message."""
    headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
    sender = _extract_email(_decode_header(headers.get("from", "")))
    subject = _decode_header(headers.get("subject", "(no subject)"))

    payload = msg["payload"]
    body = ""
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain" and "data" in part["body"]:
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                break
    elif "body" in payload and "data" in payload["body"]:
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    return sender, subject, body


def _is_reply(db: Session, org_id, thread_id: str) -> bool:
    """True if we already engaged this thread (sent or drafted) — i.e. this is a reply."""
    if not thread_id:
        return False
    return (
        db.query(Email)
        .filter(
            Email.gmail_thread_id == thread_id,
            Email.org_id == org_id,
            (Email.status == "sent") | (Email.ai_draft.isnot(None)),
        )
        .first()
        is not None
    )


def _handle_reply(db: Session, gmail: GmailClient, org, msg_id: str, thread_id: str, sender: str, subject: str, body: str):
    """Classify a reply to a sent email and route it. Returns early-exit record."""
    result = triage_agent.classify_reply(sender, subject, body)
    customer = db.query(Customer).filter(Customer.email == sender).first()

    record = Email(
        org_id=org.id,
        sender=sender,
        sender_name=customer.name if customer else None,
        subject=subject,
        body=body,
        intent="Sales",
        summary=result.summary,
        ai_draft=None,
        status="pending",
        gmail_message_id=msg_id,
        gmail_thread_id=thread_id,
        reply_intent=result.reply_intent,
    )

    if result.reply_intent == "unsubscribe":
        if customer:
            compliance.opt_out(db, customer.unsubscribe_token)
        record.status = "discarded"
        record.summary = f"[unsubscribe] {result.summary}"
        logger.info("Reply classified unsubscribe for %s — opted out", sender)
    elif result.reply_intent == "interested":
        if customer:
            set_lead_score(customer, "hot")
            if org.plan in ("growth", "scale"):
                slack_notify.notify_hot_lead(sender, customer.name, "email reply")
        # Draft a follow-up (with compliance footer) for HITL/auto handling
        context = rag_agent.retrieve(f"{subject}\n{body}")
        footer = compliance.build_footer(customer) if customer else ""
        record.ai_draft = draft_agent.draft_reply(body, customer.name if customer else None, result.summary, context, footer)
    elif result.reply_intent == "objection":
        context = rag_agent.retrieve(f"{subject}\n{body}")
        footer = compliance.build_footer(customer) if customer else ""
        record.ai_draft = draft_agent.draft_reply(body, customer.name if customer else None, f"Objection to handle: {result.summary}", context, footer)
    # not-now / referral: record only, no draft — human decides next step

    db.add(record)
    if customer:
        log_interaction(customer.id, "email", body, "inbound", db, org_id=org.id)
    db.commit()
    return record


def _process_email(gmail: GmailClient, msg: dict, org: Organization):
    msg_id = msg["id"]
    thread_id = msg["threadId"]
    sender, subject, body = _parse_payload(msg)

    # Dedup: skip if we already have this message
    db: Session = SessionLocal()
    try:
        existing = db.query(Email).filter(Email.gmail_message_id == msg_id).first()
        if existing:
            gmail.mark_read(msg_id)
            return

        # Reply routing: replies to threads we already handled get classified differently
        if _is_reply(db, org.id, thread_id):
            try:
                _handle_reply(db, gmail, org, msg_id, thread_id, sender, subject, body)
            except GroqAPIError as e:
                if "429" in str(e) or "rate_limit" in str(e):
                    db.rollback()
                    return  # ponytail: don't mark read — retry when limit resets
                logger.error("Reply classify error for %s: %s", sender, e)
                db.rollback()
            except RuntimeError as e:
                logger.error("Reply classify error for %s: %s", sender, e)
                db.rollback()
            gmail.mark_read(msg_id)
            return

        # Pre-filter: skip LLM call for obvious non-leads (saves tokens)
        if not is_potential_lead(sender, subject):
            logger.info("Skipped non-lead: %s — %s", sender, subject)
            record = Email(
                org_id=org.id,
                sender=sender,
                sender_name=None,
                subject=subject,
                body=body,
                intent="Other",
                summary="Automated/system email — no draft needed",
                ai_draft=None,
                status="pending",
                gmail_message_id=msg_id,
                gmail_thread_id=thread_id,
            )
            db.add(record)
            db.commit()
            gmail.mark_read(msg_id)
            return

        customer = upsert_customer(sender, source="email", org_id=org.id)

        # CAN-SPAM hard gate: never draft/send to opted-out contacts
        if not compliance.can_send(customer):
            logger.info("Skipped opted-out contact: %s", sender)
            record = Email(
                org_id=org.id,
                sender=sender,
                sender_name=customer.name,
                subject=subject,
                body=body,
                intent="Other",
                summary="Opted-out contact — no reply drafted",
                ai_draft=None,
                status="discarded",
                gmail_message_id=msg_id,
                gmail_thread_id=thread_id,
            )
            db.add(record)
            log_interaction(customer.id, "email", body, "inbound", db, org_id=org.id)
            db.commit()
            gmail.mark_read(msg_id)
            return

        try:
            triage = triage_agent.triage(sender, subject, body)
            if triage.sender_name and not customer.name:
                customer.name = triage.sender_name
            ai_draft = None
            if triage.should_draft and triage.intent in ("Sales", "Support"):
                context = rag_agent.retrieve(f"{subject}\n{body}")
                footer = compliance.build_footer(customer)
                ai_draft = draft_agent.draft_reply(body, triage.sender_name, triage.summary, context, footer)
        except GroqAPIError as e:
            err_str = str(e)
            if "429" in err_str or "rate_limit" in err_str:
                logger.warning("Rate limit hit — leaving unread, will retry later")
                db.rollback()
                return  # ponytail: don't mark read — retry when limit resets
            logger.error("LLM error for %s: %s", sender, e)
            gmail.mark_read(msg_id)
            return
        except RuntimeError as e:
            logger.error("LLM error for %s: %s", sender, e)
            gmail.mark_read(msg_id)
            return

        record = Email(
            org_id=org.id,
            sender=sender,
            sender_name=triage.sender_name,
            subject=subject,
            body=body,
            intent=triage.intent,
            summary=triage.summary,
            ai_draft=ai_draft,
            status="pending",
            gmail_message_id=msg_id,
            gmail_thread_id=thread_id,
        )
        db.add(record)
        db.flush()

        log_interaction(customer.id, "email", body, "inbound", db, org_id=org.id)
        if ai_draft:
            log_interaction(customer.id, "email", ai_draft, "outbound", db, org_id=org.id)

        # New hot lead → Slack (Growth plan and up) + enrichment (Scale plan)
        if triage.lead_quality == "high":
            set_lead_score(customer, "hot")
            if org.plan in ("growth", "scale"):
                slack_notify.notify_hot_lead(sender, triage.sender_name, "email")
        if org.plan == "scale" and not customer.job_title:
            enrichment_agent.enrich_customer(customer)

        if settings.MAIL_MODE == "auto" and ai_draft and compliance.can_send(customer):
            sent_id = gmail.send_reply(thread_id, sender, subject, ai_draft, msg_id)
            if sent_id:
                record.status = "sent"
                compliance.log_send(db, sender, compliance.build_footer(customer), org_id=org.id)
                logger.info("Auto-sent reply to %s (thread %s)", sender, thread_id)
            else:
                logger.warning("Auto-send failed for %s — left as pending", sender)
        else:
            logger.info("HITL: draft pending for %s", sender)

        db.commit()
        gmail.mark_read(msg_id)
    except HttpError as e:
        if e.resp.status == 401:
            logger.warning("Gmail token expired, refreshing")
            gmail.refresh()
        else:
            logger.error("Gmail API error: %s", e)
        db.rollback()
    except Exception:
        logger.exception("Unexpected error processing message %s", msg_id)
        db.rollback()
    finally:
        db.close()


def _orgs_to_poll() -> list[Organization]:
    db: Session = SessionLocal()
    try:
        return (
            db.query(Organization)
            .filter(Organization.gmail_refresh_token.isnot(None))
            .all()
        )
    finally:
        db.close()


class MailPoller:
    def __init__(self):
        self._task: asyncio.Task | None = None

    async def start(self):
        if not settings.gmail_configured:
            logger.info("Gmail not configured — poller idle")
            return
        self._task = asyncio.create_task(self._loop())
        logger.info("Mail poller started (mode=%s, interval=%ds)", settings.MAIL_MODE, settings.MAIL_POLL_INTERVAL)

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self):
        clients: dict[object, GmailClient] = {}  # ponytail: cache one client per org
        while True:
            try:
                for org in await asyncio.to_thread(_orgs_to_poll):
                    if org.id not in clients:
                        try:
                            clients[org.id] = await asyncio.to_thread(GmailClient, org)
                        except Exception:
                            logger.exception("Gmail client init failed for org %s", org.id)
                            continue
                    gmail = clients[org.id]
                    messages = await asyncio.to_thread(gmail.fetch_unread)
                    for msg in messages:
                        await asyncio.to_thread(_process_email, gmail, msg, org)
            except Exception:
                logger.exception("Poll cycle error")
            await asyncio.sleep(settings.MAIL_POLL_INTERVAL)


# ponytail: global singleton, one poller per process
poller = MailPoller()
