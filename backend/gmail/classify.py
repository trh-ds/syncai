import json

from groq import AsyncGroq

from config import settings

_client = AsyncGroq(api_key=settings.groq_api_key)

CLASSIFY_PROMPT = """You are an email triage assistant for an ASDR (AI Sales Development Rep) bot. Classify the prospect's email into one of these intents:

- "book": prospect wants to schedule a meeting/call/demo
- "question": prospect is asking questions about services/pricing
- "objection": prospect is raising objections or saying no
- "spam": this is spam, newsletter, automated reply, or not a real prospect email
- "oob": out-of-office auto-reply

Return ONLY a JSON object with these fields:
{
  "intent": "<one of the above>",
  "lead_name": "<first name or full name of sender if identifiable, otherwise empty string>",
  "summary": "<one-line summary of the email content>"
}

Do not include any other text, markdown, or explanation."""


async def classify_message(from_email: str, subject: str, body_text: str) -> dict:
    content = f"From: {from_email}\nSubject: {subject}\n\n{body_text}"

    resp = await _client.chat.completions.create(
        model=settings.groq_model_triage,
        messages=[
            {"role": "system", "content": CLASSIFY_PROMPT},
            {"role": "user", "content": content},
        ],
        temperature=0.0,
    )

    raw = resp.choices[0].message.content.strip()
    raw = raw.removeprefix("```json").removeprefix("```").rstrip("```").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"intent": "question", "lead_name": "", "summary": "unparseable"}
