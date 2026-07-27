import base64
import email.mime.text
from email.mime.text import MIMEText


def generate_reply_ref(incoming_message: dict) -> str:
    """Build In-Reply-To and References headers from incoming message headers."""
    headers = incoming_message.get("payload", {}).get("headers", [])
    header_map = {}
    for h in headers:
        header_map[h["name"].lower()] = h["value"]

    message_id = header_map.get("message-id", "")
    references = header_map.get("references", "")
    if references:
        references = references + " " + message_id if message_id else references
    else:
        references = message_id
    return message_id, references


async def send_reply(service, thread_id: str, to_email: str, reply_body: str, incoming_message: dict) -> dict:
    in_reply_to, references = generate_reply_ref(incoming_message)

    headers = incoming_message.get("payload", {}).get("headers", [])
    header_map = {}
    for h in headers:
        header_map[h["name"].lower()] = h["value"]
    original_subject = header_map.get("subject", "")
    subject = original_subject if original_subject.lower().startswith("re:") else f"Re: {original_subject}"

    msg = MIMEText(reply_body, "plain", "utf-8")
    msg["To"] = to_email
    msg["Subject"] = subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references

    raw_bytes = msg.as_bytes()
    raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode("utf-8")

    import asyncio
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: service.users().messages().send(
            userId="me",
            body={"raw": raw_b64, "threadId": thread_id},
        ).execute(),
    )
    return result
