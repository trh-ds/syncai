"""Pre-filter to avoid burning LLM tokens on bounce/auto-reply messages only.

Domain/subject filtering removed on purpose — small agencies and solo founders
often email from gmail/outlook and must never be skipped. The LLM triage agent
(with ICP context + should_draft flag) decides what deserves a reply.
"""

# ponytail: only literal machine senders — these can never be a human lead
SKIP_SENDER_PATTERNS = [
    "mailer-daemon@",
    "postmaster@",
    "bounce@",
    "auto-reply@",
    "autoresponder@",
]


def is_potential_lead(sender: str, subject: str) -> bool:
    """Return False only for machine-generated bounce/auto-reply messages."""
    sender_lower = sender.lower()
    for pattern in SKIP_SENDER_PATTERNS:
        if pattern in sender_lower:
            return False
    return True
