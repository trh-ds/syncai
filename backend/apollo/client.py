import json
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import Lead, Organization


async def sync_apollo_leads(db: AsyncSession) -> int:
    if not settings.apollo_api_key:
        return await _load_sample(db)

    query_body = json.loads(settings.apollo_saved_query_json) if settings.apollo_saved_query_json else {}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.apollo.io/v1/people/search",
            headers={
                "Content-Type": "application/json",
                "X-Api-Key": settings.apollo_api_key,
            },
            json=query_body,
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

    contacts = data.get("contacts", data.get("people", []))
    count = 0
    now = datetime.now(timezone.utc)

    for contact in contacts:
        email = contact.get("email", "")
        if not email:
            continue

        org_name = contact.get("organization_name") or contact.get("account", {}).get("name")

        lead_result = await db.execute(select(Lead).where(Lead.email == email))
        lead = lead_result.scalar_one_or_none()

        if lead:
            lead.apollo_person_id = str(contact.get("id", ""))
            lead.enriched_data = contact
            lead.title = lead.title or contact.get("title")
            lead.updated_at = now
        else:
            lead = Lead(
                email=email,
                first_name=contact.get("first_name", ""),
                last_name=contact.get("last_name", ""),
                title=contact.get("title", ""),
                linkedin_url=contact.get("linkedin_url", ""),
                source="apollo",
                status="captured",
                apollo_person_id=str(contact.get("id", "")),
                enriched_data=contact,
                last_activity_at=now,
            )

        if org_name:
            org_result = await db.execute(select(Organization).where(Organization.name == org_name))
            org = org_result.scalar_one_or_none()
            if not org:
                org = Organization(
                    name=org_name,
                    industry=contact.get("organization_industry", ""),
                    employee_count=contact.get("organization_num_employees"),
                )
                db.add(org)
                await db.flush()
            lead.org_id = org.id

        db.add(lead)
        await db.merge(lead)
        count += 1

    await db.commit()
    return count


async def _load_sample(db: AsyncSession) -> int:
    try:
        with open("seed/apollo_sample_leads.json", "r") as f:
            sample = json.load(f)
    except FileNotFoundError:
        return 0

    contacts = sample if isinstance(sample, list) else sample.get("contacts", [])
    count = 0
    now = datetime.now(timezone.utc)

    for contact in contacts:
        email = contact.get("email", "")
        if not email:
            continue

        lead_result = await db.execute(select(Lead).where(Lead.email == email))
        if lead_result.scalar_one_or_none():
            continue

        lead = Lead(
            email=email,
            first_name=contact.get("first_name", ""),
            last_name=contact.get("last_name", ""),
            title=contact.get("title", ""),
            linkedin_url=contact.get("linkedin_url", ""),
            source="apollo",
            status="captured",
            apollo_person_id=str(contact.get("id", "")),
            enriched_data=contact,
            last_activity_at=now,
        )
        db.add(lead)
        count += 1

    await db.commit()
    return count
