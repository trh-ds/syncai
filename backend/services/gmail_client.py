import base64
import email.mime.text
import logging
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from core.config import settings

logger = logging.getLogger("gmail")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


def _creds(refresh_token: str | None = None) -> Credentials:
    c = Credentials(
        token=None,
        refresh_token=refresh_token or settings.GMAIL_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GMAIL_CLIENT_ID,
        client_secret=settings.GMAIL_CLIENT_SECRET,
        scopes=SCOPES,
    )
    c.refresh(Request())
    return c


# ponytail: simple wrapper, add connection pooling if throughput matters
class GmailClient:
    def __init__(self, org=None):
        # Per-org token from onboarding OAuth; falls back to env-based single-tenant creds
        token = getattr(org, "gmail_refresh_token", None) if org is not None else None
        self.org = org
        self.service = build("gmail", "v1", credentials=_creds(token))

    def fetch_unread(self) -> list[dict]:
        """Return list of unread messages with full payload, newest first."""
        try:
            result = (
                self.service.users()
                .messages()
                .list(userId="me", q="is:unread", maxResults=10)
                .execute()
            )
        except HttpError as e:
            logger.error("Gmail list failed: %s", e)
            return []

        messages = result.get("messages", [])
        if not messages:
            return []

        full = []
        for m in messages:
            try:
                msg = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=m["id"], format="full")
                    .execute()
                )
                full.append(msg)
            except HttpError as e:
                logger.error("Gmail get message %s failed: %s", m["id"], e)
        return full

    def send_reply(
        self, thread_id: str, to: str, subject: str, body: str, message_id: str
    ) -> Optional[str]:
        """Send a reply in the same thread. Returns the sent message id or None."""
        msg = email.mime.text.MIMEText(body)
        msg["To"] = to
        msg["Subject"] = f"Re: {subject}"
        msg["In-Reply-To"] = message_id
        msg["References"] = message_id

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        try:
            sent = (
                self.service.users()
                .messages()
                .send(
                    userId="me",
                    body={"raw": raw, "threadId": thread_id},
                )
                .execute()
            )
            return sent["id"]
        except HttpError as e:
            logger.error("Gmail send failed: %s", e)
            return None

    def mark_read(self, msg_id: str) -> bool:
        """Remove UNREAD label from a message."""
        try:
            self.service.users().messages().modify(
                userId="me",
                id=msg_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
            return True
        except HttpError as e:
            logger.error("Gmail mark read %s failed: %s", msg_id, e)
            return False

    def refresh(self):
        """Rebuild the service with fresh credentials (call on HttpError 401)."""
        token = getattr(self.org, "gmail_refresh_token", None) if self.org is not None else None
        self.service = build("gmail", "v1", credentials=_creds(token))
