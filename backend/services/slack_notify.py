"""Slack incoming-webhook notifications. No-op when SLACK_WEBHOOK_URL is unset."""

import logging

import httpx

from core.config import settings

logger = logging.getLogger("slack")


def notify(text: str) -> bool:
    if not settings.SLACK_WEBHOOK_URL:
        return False
    try:
        resp = httpx.post(settings.SLACK_WEBHOOK_URL, json={"text": text}, timeout=5.0)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.warning("Slack notify failed: %s", e)
        return False


def notify_hot_lead(email: str, name: str | None, source: str) -> bool:
    return notify(f"🔥 New HOT lead: {name or email} <{email}> via {source}")


def notify_meeting(summary: str, start_iso: str) -> bool:
    return notify(f"📅 Meeting booked: {summary} at {start_iso}")
