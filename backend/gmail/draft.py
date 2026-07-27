import os

from groq import AsyncGroq

from config import settings

_client = AsyncGroq(api_key=settings.groq_api_key)

_AGENCY_INFO: str | None = None


def _load_agency_info() -> str:
    global _AGENCY_INFO
    if _AGENCY_INFO is None:
        path = os.path.join(os.path.dirname(__file__), "..", "seed", "agency_info.txt")
        try:
            with open(path, "r", encoding="utf-8") as f:
                _AGENCY_INFO = f.read()
        except FileNotFoundError:
            _AGENCY_INFO = ""
    return _AGENCY_INFO


DRAFT_SYSTEM = """You are Maya, an AI Sales Development Rep for the agency described below.

AGENCY KNOWLEDGE BASE:
{agency_info}

Your tone: warm, helpful, concise, human. Write like a real person — not corporate, not robotic. Keep it under 150 words.

Rules:
- If the prospect asked a question, answer it using info from the knowledge base (services, pricing, clients, etc.)
- If they want to book, confirm enthusiasm and ask for a time.
- If they raised an objection, acknowledge it respectfully and offer a brief counter or alternative view.
- Always end with a soft call-to-action: suggest a free 30-min brand audit call.
- Do NOT say "I am an AI" or "as an AI". Just be Maya.
- Use the prospect's name if you know it. Otherwise use a friendly generic greeting.
- Ground your reply in the knowledge base — be specific about services, pricing, or results if relevant."""


async def draft_reply(inbound_message: dict, lead_context: str = "") -> str:
    model = settings.groq_model_draft
    if settings.groq_model_draft_fast_fallback:
        model = settings.groq_model_triage

    user_content = f"Prospect email:\nFrom: {inbound_message.get('from_email', '')}\nSubject: {inbound_message.get('subject', '')}\nBody: {inbound_message.get('body_text', '')}\n\nIntent classification: {inbound_message.get('intent', 'unknown')}\nLead context: {lead_context}"

    resp = await _client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": DRAFT_SYSTEM.format(agency_info=_load_agency_info())},
            {"role": "user", "content": user_content},
        ],
        temperature=0.7,
    )

    return resp.choices[0].message.content.strip()
