"""Idempotent seed script — seeds only leads + organizations from sample data.
No fake emails, meetings, chat sessions, or activity events. Those come from live integrations."""
import asyncio
import json
import os
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, delete

from db.init_db import init_db
from db.session import async_session
from models import Organization, Lead, KV, DemoMetricsCache

APOLLO_SAMPLE_PATH = os.path.join(os.path.dirname(__file__), "apollo_sample_leads.json")

NOW = datetime.now(timezone.utc)


async def seed():
    if os.environ.get("ENV") != "dev":
        print("ENV is not 'dev'. Refusing to seed. Set ENV=dev to proceed.")
        return

    print("Initializing DB...")
    await init_db()

    async with async_session() as db:
        print("Wiping existing data...")
        for table in [DemoMetricsCache, KV, Lead, Organization]:
            await db.execute(delete(table))

        # --- Organizations + Leads from Apollo sample JSON ---
        print("Seeding organizations and leads from sample data...")
        with open(APOLLO_SAMPLE_PATH) as f:
            sample_leads = json.load(f)

        org_cache: dict[str, Organization] = {}
        count = 0
        for sl in sample_leads:
            org_data = sl.get("organization", {})
            org_name = org_data.get("name", "")
            org = org_cache.get(org_name)
            if not org and org_name:
                org = Organization(
                    id=uuid4(),
                    name=org_name,
                    industry=org_data.get("industry", ""),
                    employee_count=org_data.get("employee_count"),
                )
                db.add(org)
                await db.flush()
                org_cache[org_name] = org

            lead = Lead(
                id=uuid4(),
                org_id=org.id if org else None,
                first_name=sl.get("first_name", ""),
                last_name=sl.get("last_name", ""),
                email=sl["email"],
                title=sl.get("title", ""),
                linkedin_url=sl.get("linkedin_url", ""),
                source="apollo_sample",
                status="captured",
                enriched_data=sl,
                last_activity_at=NOW,
                created_at=NOW,
                updated_at=NOW,
            )
            db.add(lead)
            count += 1

        # --- KV ---
        db.add(KV(key="gmail_last_history_id", value="0"))

        # --- Metrics cache (zeros — will recompute from real data) ---
        db.add(DemoMetricsCache(
            id=1, leads_count=count, meetings_count=0,
            est_cost_saved=0, est_hours_saved=0,
            avg_reply_latency_ms=0, success_rate=0,
        ))

        await db.commit()
        print(f"Seeded: {count} leads from sample data. No fake emails/meetings/chat/activity — those come from live integrations.")


if __name__ == "__main__":
    asyncio.run(seed())
