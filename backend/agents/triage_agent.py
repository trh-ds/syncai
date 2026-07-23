from typing import Optional

from groq import Groq
from pydantic import BaseModel, ValidationError

from core.config import settings
from models.email import Intent

ICP_CONTEXT = """Our Ideal Customer Profile (ICP):
- Business type: SMB, startup, or mid-market company
- Looking for: digital marketing services (SEO, PPC, social media marketing, content marketing, email marketing, web design, branding, advertising)
- Has: a budget, a timeline, a specific pain point or project in mind

NOT our ICP:
- Job seekers or applicants
- Automated system notifications (AWS, Google, security alerts)
- Newsletters, promotional emails, product announcements
- SaaS trial notifications
- Social media notifications
- E-commerce marketing emails
- Invoice/billing/payment reminders"""

TRIAGE_SYSTEM_PROMPT = """You are an expert sales operations assistant for {company}.

{icp}

Read the provided email. Extract:
1. intent: exactly one of Sales, Support, Spam, Other
2. sender_name: the human sender's name (null if automated/unknown)
3. summary: 1 sentence describing what they want
4. should_draft: true ONLY if this is a genuine business inquiry matching our ICP and deserves a personalized reply. false for everything else.
5. lead_quality: "high" if strong buying signals (budget, timeline, specific need), "medium" if interested but vague, "low" for everything else

Output strictly in JSON format:
{{"intent": "Sales | Support | Spam | Other", "sender_name": "Name or null", "summary": "1 sentence", "should_draft": true, "lead_quality": "high | medium | low"}}"""


class TriageResult(BaseModel):
    intent: Intent
    sender_name: Optional[str] = None
    summary: str
    should_draft: bool = False
    lead_quality: str = "low"


def _client() -> Groq:
    return Groq(api_key=settings.require_groq_key())


def triage(sender: str, subject: str, body: str) -> TriageResult:
    completion = _client().chat.completions.create(
        model=settings.GROQ_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": TRIAGE_SYSTEM_PROMPT.format(
                    company=settings.CLIENT_COMPANY_NAME,
                    icp=ICP_CONTEXT,
                ),
            },
            {"role": "user", "content": f"From: {sender}\nSubject: {subject}\n\n{body}"},
        ],
    )
    try:
        return TriageResult.model_validate_json(completion.choices[0].message.content)
    except ValidationError as e:
        raise RuntimeError(f"Triage agent returned invalid JSON: {e}") from e
