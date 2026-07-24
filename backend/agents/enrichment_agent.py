"""Apollo.io lead enrichment — light per-lead lookups only (free credit limits).

One call per NEW customer, only for orgs on the Scale plan. No bulk prospecting.
"""

import logging

import httpx

from core.config import settings
from models.customer import Customer

logger = logging.getLogger("enrichment")

APOLLO_MATCH_URL = "https://api.apollo.io/api/v1/people/match"


def enrich_customer(customer: Customer) -> bool:
    """Fill job_title/company_size on the customer row. Returns True if enriched."""
    if not settings.APOLLO_API_KEY:
        return False
    try:
        resp = httpx.post(
            APOLLO_MATCH_URL,
            headers={"X-Api-Key": settings.APOLLO_API_KEY, "Content-Type": "application/json"},
            json={"email": customer.email},
            timeout=10.0,
        )
        resp.raise_for_status()
        person = resp.json().get("person") or {}
    except Exception as e:
        logger.warning("Apollo lookup failed for %s: %s", customer.email, e)
        return False

    org = person.get("organization") or {}
    size = org.get("estimated_num_employees")
    customer.job_title = person.get("title") or customer.job_title
    customer.company_size = str(size) if size else customer.company_size
    return bool(person)
