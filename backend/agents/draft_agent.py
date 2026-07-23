from groq import Groq

from core.config import settings

DRAFT_SYSTEM_PROMPT = """You are a helpful, professional Account Executive at {company}.
A prospective lead has emailed you.
Here is the lead's email: {original_email}
Triage summary: {summary}
Here is relevant information from your company's knowledge base: {rag_context}

Write a concise, friendly, and highly personalized reply to the lead. Address their specific pain points using the knowledge base context. Do not sound robotic or use generic sales jargon. Include a call to action to book a meeting.

IMPORTANT: End your reply by inviting the lead to continue the conversation on our live chat assistant for instant answers and faster booking. Say something like: "For immediate assistance or to book a meeting right now, chat with our AI assistant at {chatbot_url} — it can answer your questions and find the perfect time for a call." """


def draft_reply(original_email: str, sender_name: str | None, summary: str, rag_context: str) -> str:
    prompt = DRAFT_SYSTEM_PROMPT.format(
        company=settings.CLIENT_COMPANY_NAME,
        original_email=original_email,
        summary=summary,
        rag_context=rag_context or "(no knowledge base context available)",
        chatbot_url=settings.CHATBOT_URL,
    )
    if sender_name:
        prompt += f"\nAddress the lead by name: {sender_name}."
    completion = Groq(api_key=settings.require_groq_key()).chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": "Write the reply now."},
        ],
    )
    return completion.choices[0].message.content.strip()
