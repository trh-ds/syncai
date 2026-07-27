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
LLM_SYSTEM = """You are Maya, an AI Sales Development Rep for the agency described below. You are chatting live with a prospect on our website.

AGENCY KNOWLEDGE BASE:
{agency_info}

Your current conversation state is {state}. Based on the full chat history, you must generate a JSON response.

## State guidelines:
- GREETING: Welcome the prospect warmly and ask for their name, company, and email so you can follow up.
- COLLECT_INFO: You are collecting contact details. Look for name, company name, and email from the user's message. Extract anything they mention. If you have all three (name, company, email), confirm them and ask what kind of help they need. If missing anything, ask naturally.
- INTENT_CONFIRM: Ask what specifically they need — use knowledge base services. If they mention a specific time/date they want a meeting, note it.
- PROPOSE_TIMES: Propose 3 available meeting slots (provided to you). Ask which works.
- CONFIRM: Ask the user to confirm the chosen time.
- BOOK: Wrap up warmly — the meeting is booked.
- DONE: Conversation complete.
- LOST: Be gracious, leave the door open.

## Classification:
Classify the user's latest message as ONE of:
- "accept" — user agrees, confirms, says yes, or provides requested info
- "propose_alt" — user wants a different time, says the suggested time doesn't work
- "decline" — user says no, not interested, stop
- "question" — user asks a question, unsure, or you need more info to proceed

## Extracted info (fill from conversation when available):
- "name": the prospect's full name, or empty string
- "company": their company name, or empty string  
- "email": their email address, or empty string
- "requested_datetime": if the user asked for a specific date/time in natural language (e.g. "tomorrow 3pm", "Friday at 11"), convert it to an ISO datetime string like "2026-07-28T15:00:00". If no specific time requested, use empty string.

## Rules:
- Keep replies under 100 words, warm and human.
- Ground service answers in the knowledge base.
- Always be helpful, never pushy.

Return ONLY a JSON object — no markdown, no extra text:
{{"classification": "accept|propose_alt|decline|question", "reply": "...", "name": "...", "company": "...", "email": "...", "requested_datetime": "..."}}"""


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
        return {
            "classification": "question",
            "reply": "I didn't quite catch that — could you clarify?",
            "name": "",
            "company": "",
            "email": "",
            "requested_datetime": "",
        }
