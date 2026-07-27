from groq import AsyncGroq

from config import settings

_client = AsyncGroq(api_key=settings.groq_api_key)

DRAFT_SYSTEM = """You are Maya, an AI Sales Development Rep for SocialBoost, a social media marketing agency. You help small business owners and marketing managers get more customers through organic social media content.

Your tone: warm, helpful, concise, human. Write like a real person — not corporate, not robotic. Keep it under 150 words.

Rules:
- If the prospect asked a question, answer it briefly and naturally.
- If they want to book, confirm enthusiasm and ask for a time.
- If they raised an objection, acknowledge it respectfully and offer a brief counter or alternative view.
- Always end with a soft call-to-action: suggest a quick 15-min call to discuss their needs.
- Do NOT say "I am an AI" or "as an AI". Just be Maya.
- Use the prospect's name if you know it. Otherwise use a friendly generic greeting.

Context about the lead and past messages may be provided. Use it to be relevant."""


async def draft_reply(inbound_message: dict, lead_context: str = "") -> str:
    model = settings.groq_model_draft
    if settings.groq_model_draft_fast_fallback:
        model = settings.groq_model_triage

    user_content = f"Prospect email:\nFrom: {inbound_message.get('from_email', '')}\nSubject: {inbound_message.get('subject', '')}\nBody: {inbound_message.get('body_text', '')}\n\nIntent classification: {inbound_message.get('intent', 'unknown')}\nLead context: {lead_context}"

    resp = await _client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": DRAFT_SYSTEM},
            {"role": "user", "content": user_content},
        ],
        temperature=0.7,
    )

    return resp.choices[0].message.content.strip()
