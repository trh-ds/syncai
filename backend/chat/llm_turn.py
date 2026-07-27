import json

from groq import AsyncGroq

from config import settings

_client = AsyncGroq(api_key=settings.groq_api_key)

LLM_SYSTEM = """You are Maya, an AI Sales Development Rep for SocialBoost, a social media marketing agency. You are chatting live with a prospect on our website.

Your current conversation state is {state}. Based on the full chat history, you must:
1. Classify the user's latest message as: "accept", "propose_alt", "decline", or "question"
2. Generate a short, natural, helpful reply (under 100 words).

Guidelines per state:
- GREETING: welcome the prospect, ask how you can help
- INTENT_CONFIRM: confirm what they need (content creation, social media management, ads, etc.)
- PROPOSE_TIMES: you proposed meeting times — user may accept, suggest alternates, or decline
- CONFIRM: confirm the final chosen time
- BOOK: meeting booked, wrap up warmly
- DONE: conversation complete
- LOST: prospect not interested, be gracious

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

    system = LLM_SYSTEM.format(state=session.state)

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
