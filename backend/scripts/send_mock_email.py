"""Send a sample inbound email payload to the webhook.

Usage: python scripts/send_mock_email.py [sales|spam] [base_url]
"""
import sys

import httpx

SAMPLES = {
    "sales": {
        "sender": "jane@acmeplumbing.com",
        "subject": "Pricing question for website redesign",
        "body": "Hi, I'm Jane from Acme Plumbing. Our website is ancient and we're losing leads. What does a website redesign cost, and how long would it take? Also curious if you do local SEO.",
    },
    "spam": {
        "sender": "winner@lottery-central.biz",
        "subject": "CONGRATULATIONS you WON $1,000,000!!!",
        "body": "Dear lucky winner, claim your prize NOW by sending your bank details and a small processing fee. Act fast, this offer expires today!",
    },
}

base_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"
sample = SAMPLES.get(sys.argv[1] if len(sys.argv) > 1 else "sales", SAMPLES["sales"])

resp = httpx.post(f"{base_url}/api/v1/webhooks/email", json=sample, timeout=60)
print(resp.status_code)
print(resp.json())
