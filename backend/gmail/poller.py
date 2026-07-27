import asyncio
import logging
from datetime import datetime, timezone

from googleapiclient.discovery import build
from sqlalchemy import select

from config import settings
from db.session import async_session
from events import emit
from gmail.oauth import get_credentials
from gmail.classify import classify_message
from gmail.draft import draft_reply
from gmail.send import send_reply, generate_reply_ref
from models import Lead, EmailThread, EmailMessage, KV, ActivityEvent

logger = logging.getLogger("poller")


def _extract_header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _get_body(payload: dict) -> str:
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                import base64
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        for part in payload["parts"]:
            if part.get("body", {}).get("data"):
                import base64
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
    if payload.get("body", {}).get("data"):
        import base64
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    return ""


async def _get_kv(key: str) -> str | None:
    async with async_session() as db:
        result = await db.execute(select(KV).where(KV.key == key))
        row = result.scalar_one_or_none()
        return row.value if row else None


async def _set_kv(key: str, value: str):
    async with async_session() as db:
        row = KV(key=key, value=value)
        await db.merge(row)
        await db.commit()


async def _message_exists(gmail_message_id: str) -> bool:
    async with async_session() as db:
        result = await db.execute(
            select(EmailMessage).where(EmailMessage.gmail_message_id == gmail_message_id)
        )
        return result.scalar_one_or_none() is not None


async def gmail_poller():
    logger.info("Gmail poller starting...")
    if not settings.gmail_refresh_token:
        logger.warning("No GMAIL_REFRESH_TOKEN set — poller will idle")
        await asyncio.Event().wait()
        return

    while True:
        try:
            creds = await get_credentials()
            service = build("gmail", "v1", credentials=creds)

            last_history_id = await _get_kv("gmail_last_history_id")
            if not last_history_id or last_history_id == "0":
                profile = service.users().getProfile(userId="me").execute()
                last_history_id = str(profile.get("historyId", "1"))
                await _set_kv("gmail_last_history_id", last_history_id)

            poll_interval = max(settings.gmail_poll_interval_ms / 1000, 5)

            while True:
                try:
                    await asyncio.sleep(poll_interval)

                    history_resp = service.users().history().list(
                        userId="me",
                        historyTypes="messageAdded",
                        labelId="INBOX",
                        startHistoryId=last_history_id,
                    ).execute()

                    for history in history_resp.get("history", []):
                        for msg_added in history.get("messagesAdded", []):
                            msg_id = msg_added["message"]["id"]
                            await _process_inbound(service, msg_id)
                        last_history_id = str(history["id"])

                    if history_resp.get("history"):
                        await _set_kv("gmail_last_history_id", last_history_id)

                except Exception as e:
                    logger.error(f"Poll error: {e}", exc_info=True)
                    break  # re-auth on error

        except Exception as e:
            logger.error(f"Poller outer error: {e}", exc_info=True)
            await asyncio.sleep(30)


async def _process_inbound(service, msg_id: str):
    try:
        import asyncio as aio
        loop = aio.get_running_loop()
        msg = await loop.run_in_executor(
            None,
            lambda: service.users().messages().get(userId="me", id=msg_id, format="full").execute(),
        )
    except Exception as e:
        logger.error(f"Failed to fetch message {msg_id}: {e}")
        return

    if await _message_exists(msg["id"]):
        return

    headers = msg.get("payload", {}).get("headers", [])
    from_email = _extract_header(headers, "From")
    if "<" in from_email and ">" in from_email:
        from_email = from_email.split("<")[1].split(">")[0]
    subject = _extract_header(headers, "Subject")
    body_text = _get_body(msg.get("payload", {}))

    if not from_email:
        return

    if settings.gmail_monitored_email and settings.gmail_monitored_email.lower() in from_email.lower():
        return

    gmail_thread_id = msg["threadId"]
    arrived_at = datetime.fromtimestamp(int(msg["internalDate"]) / 1000, tz=timezone.utc)

    async with async_session() as db:
        lead_result = await db.execute(select(Lead).where(Lead.email == from_email))
        lead = lead_result.scalar_one_or_none()
        if not lead:
            lead = Lead(
                email=from_email,
                source="email_inbound",
                status="captured",
                last_activity_at=datetime.now(timezone.utc),
            )
            db.add(lead)
            await db.flush()
        else:
            lead.last_activity_at = datetime.now(timezone.utc)

        thread_result = await db.execute(
            select(EmailThread).where(EmailThread.gmail_thread_id == gmail_thread_id)
        )
        thread = thread_result.scalar_one_or_none()
        if not thread:
            thread = EmailThread(
                lead_id=lead.id,
                gmail_thread_id=gmail_thread_id,
                subject=subject,
                status="open",
            )
            db.add(thread)
            await db.flush()

        email_msg = EmailMessage(
            thread_id=thread.id,
            gmail_message_id=msg["id"],
            direction="inbound",
            from_email=from_email,
            subject=subject,
            body_text=body_text,
            arrived_at=arrived_at,
        )
        db.add(email_msg)
        await db.flush()

        msg_id_for_log = email_msg.id
        await db.commit()

    try:
        classification = await classify_message(from_email, subject, body_text)
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        classification = {"intent": "question", "lead_name": "", "summary": ""}

    intent = classification.get("intent", "question")

    async with async_session() as db:
        em = await db.get(EmailMessage, msg_id_for_log)
        if em:
            em.intent = intent
            await db.commit()

    await emit({
        "type": "email_received",
        "lead_id": str(lead.id),
        "payload": {
            "gmail_message_id": msg["id"],
            "from_email": from_email,
            "subject": subject,
            "intent": intent,
        },
    })

    if intent in ("book", "question", "objection"):
        try:
            reply_text = await draft_reply({
                "from_email": from_email,
                "subject": subject,
                "body_text": body_text,
                "intent": intent,
            })

            send_result = await send_reply(service, gmail_thread_id, from_email, reply_text, msg)

            now = datetime.now(timezone.utc)
            latency = int((now - arrived_at).total_seconds() * 1000) if arrived_at else None

            async with async_session() as db:
                out_msg = EmailMessage(
                    thread_id=thread.id,
                    gmail_message_id=send_result.get("id", ""),
                    direction="outbound",
                    from_email="",
                    to_email=from_email,
                    subject=f"Re: {subject}",
                    body_text=reply_text,
                    sent_at=now,
                    reply_latency_ms=latency,
                )
                db.add(out_msg)
                lead_obj = await db.get(Lead, lead.id)
                if lead_obj:
                    lead_obj.status = "contacted"
                    lead_obj.last_activity_at = now
                await db.commit()

            await emit({
                "type": "email_sent",
                "lead_id": str(lead.id),
                "payload": {
                    "to_email": from_email,
                    "subject": f"Re: {subject}",
                    "intent": intent,
                },
            })

        except Exception as e:
            logger.error(f"Reply flow failed for {from_email}: {e}")
