import json
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


# ponytail: simple file-based RAG — one agency doc, no vector DB needed for a demo.
# upgrade path: ChromaDB collection with chunked docs if knowledge base grows.
LLM_SYSTEM = """You are Maya, an AI Sales Development Rep for the agency described below. You are chatting live with a prospect on our website.

AGENCY KNOWLEDGE BASE:
{agency_info}

Your current conversation state is {state}. Based on the full chat history, you must:
1. Classify the user's latest message as: "accept", "propose_alt", "decline", or "question"
2. Generate a short, natural, helpful reply (under 100 words).

Guidelines per state:
- GREETING: welcome the prospect, ask how you can help
- INTENT_CONFIRM: confirm what they need — reference specific services from the knowledge base if relevant
- PROPOSE_TIMES: you proposed meeting times — user may accept, suggest alternates, or decline
- CONFIRM: confirm the final chosen time
- BOOK: meeting booked, wrap up warmly
- DONE: conversation complete
- LOST: prospect not interested, be gracious

When the prospect asks about services, pricing, or past work, ground your answer in the knowledge base above. Be specific — mention real services, starting prices, or client results if relevant.

If proposing times: suggest 3 slots clear and ordered.

Return ONLY a JSON object:
{{"classification": "accept|propose_alt|decline|question", "reply": "..."}}"""


async def process_turn(session, user_message: str, chat_history: list) -> dict:
    model = settings.groq_model_draft
    if settings.groq_model_draft_fast_fallback:
        model = settings.groq_model_triage

    history_text = "\n".join(
        [f"{'Prospect' if m.direction == 'inbound' else 'Maya'}: {m.text}" for m in chat_history[-10:]]
    )
    if not history_text:
        history_text = "(no history)"

    system = LLM_SYSTEM.format(
        agency_info=_load_agency_info(),
        state=session.state,
    )

    resp = await _client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Chat history:\n{history_text}\n\nLatest prospect message: {user_message}"},
        ],
        temperature=0.7,
    )

    raw = resp.choices[0].message.content.strip()
    raw = raw.removeprefix("```json").removeprefix("```").rstrip("```").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"classification": "question", "reply": "I didn't quite catch that — could you clarify?"}
