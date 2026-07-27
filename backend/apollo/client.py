import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Lead, Organization


async def sync_apollo_leads(db: AsyncSession) -> int:
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

        result = await db.execute(select(Lead).where(Lead.email == email))
        if result.scalar_one_or_none():
            continue

        org_data = contact.get("organization", {})
        org_name = org_data.get("name", "")

        org_id = None
        if org_name:
            org_result = await db.execute(select(Organization).where(Organization.name == org_name))
            org = org_result.scalar_one_or_none()
            if not org:
                org = Organization(
                    name=org_name,
                    industry=org_data.get("industry", ""),
                    employee_count=org_data.get("employee_count"),
                )
                db.add(org)
                await db.flush()
            org_id = org.id

        lead = Lead(
            email=email,
            first_name=contact.get("first_name", ""),
            last_name=contact.get("last_name", ""),
            title=contact.get("title", ""),
            linkedin_url=contact.get("linkedin_url", ""),
            source="apollo_sample",
            status="captured",
            org_id=org_id,
            enriched_data=contact,
            last_activity_at=now,
        )
        db.add(lead)
        count += 1

    await db.commit()
    return count
