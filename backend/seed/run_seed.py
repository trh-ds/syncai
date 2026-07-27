"""Idempotent seed script — wipes and recreates demo data. Guarded by ENV=dev check."""
import asyncio
import json
import os
import random
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, delete, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from db.init_db import init_db
from db.session import async_session
from models import (
    Organization, Lead, EmailThread, EmailMessage,
    ChatSession, ChatMessage, Meeting, ActivityEvent, DemoMetricsCache,
)
from seed.reply_templates import REPLY_TEMPLATES

APOLLO_SAMPLE_PATH = os.path.join(os.path.dirname(__file__), "apollo_sample_leads.json")

STATUSES = ["captured", "contacted", "replied", "booked", "no_show", "lost"]
INTENTS = ["book", "question", "objection", "spam", "oob"]
ACTIVITY_TYPES = [
    "email_inbound", "email_outbound", "chat_message", "meeting_booked",
    "lead_status_change", "apollo_sync"
]
CHAT_STATES = ["GREETING", "INTENT_CONFIRM", "PROPOSE_TIMES", "CONFIRM", "BOOK", "DONE", "LOST"]

NOW = datetime.now(timezone.utc)
DAYS_14 = NOW - timedelta(days=14)


def _rand_time(days_ago: int = 0) -> datetime:
    base = NOW - timedelta(days=days_ago)
    offset = timedelta(hours=random.randint(1, 23), minutes=random.randint(0, 59))
    return base.replace(hour=0, minute=0, second=0, microsecond=0) + offset


def _days_ago(d: int) -> datetime:
    return NOW - timedelta(days=d)


async def seed():
    if os.environ.get("ENV") != "dev":
        print("ENV is not 'dev'. Refusing to seed. Set ENV=dev to proceed.")
        return

    print("Initializing DB...")
    await init_db()

    async with async_session() as db:
        print("Wiping existing data...")
        for table in [ActivityEvent, ChatMessage, ChatSession, Meeting, EmailMessage, EmailThread, Lead, Organization, DemoMetricsCache]:
            await db.execute(delete(table))

        # --- Organizations ---
        print("Seeding organizations and leads...")
        sample_leads = []
        with open(APOLLO_SAMPLE_PATH) as f:
            sample_leads = json.load(f)

        orgs = {}
        for sl in sample_leads:
            o = Organization(
                id=uuid4(),
                name=sl["organization"]["name"],
                industry=sl["organization"]["industry"],
                employee_count=sl["organization"]["employee_count"],
            )
            db.add(o)
            orgs[sl["organization"]["name"]] = o

        # 4 extra orgs for variety
        extra_orgs = [
            Organization(id=uuid4(), name="PixelPop", industry="Creative Agency", employee_count=10),
            Organization(id=uuid4(), name="MetricMax", industry="Analytics & Reporting", employee_count=12),
            Organization(id=uuid4(), name="CreatorEngine", industry="Influencer Platform", employee_count=20),
            Organization(id=uuid4(), name="ScaleUp Media", industry="Growth Marketing", employee_count=4),
        ]
        for o in extra_orgs:
            db.add(o)

        await db.flush()

        all_orgs = orgs | {o.name: o for o in extra_orgs}
        org_list = list(all_orgs.values())

        # --- Leads (24 total) ---
        # 8 apollo → captured
        # 6 apollo_sample → contacted
        # 4 email_inbound → replied
        # 4 apollo → booked
        # 1 apollo_sample → no_show
        # 1 email_inbound → lost
        leads_data = []
        for i, sl in enumerate(sample_leads[:8]):
            leads_data.append({
                "org": orgs[sl["organization"]["name"]],
                "first_name": sl["first_name"], "last_name": sl["last_name"],
                "email": sl["email"], "title": sl["title"],
                "linkedin_url": sl.get("linkedin_url", ""), "source": "apollo",
                "status": "captured", "apollo_person_id": f"apollo_{i}",
                "enriched_data": sl, "days": random.randint(1, 14),
            })
        for i, sl in enumerate(sample_leads[8:14]):
            leads_data.append({
                "org": orgs[sl["organization"]["name"]],
                "first_name": sl["first_name"], "last_name": sl["last_name"],
                "email": sl["email"], "title": sl["title"],
                "linkedin_url": sl.get("linkedin_url", ""), "source": "apollo_sample",
                "status": "contacted", "apollo_person_id": None,
                "enriched_data": sl, "days": random.randint(4, 12),
            })
        for i, sl in enumerate(sample_leads[14:18]):
            leads_data.append({
                "org": orgs[sl["organization"]["name"]],
                "first_name": sl["first_name"], "last_name": sl["last_name"],
                "email": sl["email"], "title": sl["title"],
                "linkedin_url": sl.get("linkedin_url", ""), "source": "email_inbound",
                "status": "replied", "apollo_person_id": None,
                "enriched_data": sl, "days": random.randint(2, 10),
            })
        for i, sl in enumerate(sample_leads[18:20]):
            leads_data.append({
                "org": orgs[sl["organization"]["name"]],
                "first_name": sl["first_name"], "last_name": sl["last_name"],
                "email": sl["email"], "title": sl["title"],
                "linkedin_url": sl.get("linkedin_url", ""), "source": "apollo",
                "status": "booked", "apollo_person_id": f"apollo_{18+i}",
                "enriched_data": sl, "days": random.randint(1, 8),
            })
        # 2 more booked
        leads_data.append({
            "org": extra_orgs[0], "first_name": "Sachin", "last_name": "Tendulkar",
            "email": "sachin@pixelpop.co", "title": "Co-Founder",
            "linkedin_url": "https://linkedin.com/in/sachint", "source": "apollo",
            "status": "booked", "apollo_person_id": "apollo_20", "enriched_data": {}, "days": 3,
        })
        leads_data.append({
            "org": extra_orgs[1], "first_name": "Nitin", "last_name": "Bose",
            "email": "nitin@metricmax.in", "title": "CEO",
            "linkedin_url": "https://linkedin.com/in/nitinbose", "source": "email_inbound",
            "status": "booked", "apollo_person_id": None, "enriched_data": {}, "days": 5,
        })
        # 1 no_show
        leads_data.append({
            "org": org_list[15], "first_name": "Ritu", "last_name": "Chopra",
            "email": "ritu@engagefirst.co", "title": "Marketing Director",
            "linkedin_url": "https://linkedin.com/in/rituchopra", "source": "apollo_sample",
            "status": "no_show", "apollo_person_id": None, "enriched_data": {}, "days": 7,
        })
        # 1 lost
        leads_data.append({
            "org": org_list[16], "first_name": "Deepak", "last_name": "Agarwal",
            "email": "deepak@creatorengine.io", "title": "VP Growth",
            "linkedin_url": "https://linkedin.com/in/deepakagarwal", "source": "email_inbound",
            "status": "lost", "apollo_person_id": None, "enriched_data": {}, "days": 10,
        })

        leads = {}
        for ld in leads_data:
            t = _rand_time(ld["days"])
            lead = Lead(
                id=uuid4(), org_id=ld["org"].id,
                first_name=ld["first_name"], last_name=ld["last_name"],
                email=ld["email"], title=ld["title"],
                linkedin_url=ld["linkedin_url"], source=ld["source"],
                status=ld["status"], apollo_person_id=ld["apollo_person_id"],
                enriched_data=ld["enriched_data"], last_activity_at=t,
                created_at=t, updated_at=t,
            )
            db.add(lead)
            leads[ld["email"]] = lead

        await db.flush()

        # --- Email Threads & Messages (~30 threads) ---
        print("Seeding email threads and messages...")
        thread_count = 0
        for email, lead in leads.items():
            if thread_count >= 30:
                break
            status = lead.status
            if status in ["captured", "no_show"]:
                continue  # captured leads haven't been emailed yet per status

            gmail_tid = f"thread-seed-{thread_count}"
            thread = EmailThread(
                id=uuid4(), lead_id=lead.id, gmail_thread_id=gmail_tid,
                subject=f"Quick question about your services",
                status="open",
            )
            db.add(thread)

            arrived = _rand_time(random.randint(1, 13))
            inbound = EmailMessage(
                id=uuid4(), thread_id=thread.id,
                gmail_message_id=f"msg-seed-in-{thread_count}",
                direction="inbound", from_email=email,
                to_email="asdr.demo@gmail.com",
                subject=thread.subject,
                body_text="Hi Maya, I run a social media agency and we're struggling with outbound. Can you help?",
                intent="question", intent_confidence=0.92,
                reply_latency_ms=None, arrived_at=arrived, sent_at=arrived,
                created_at=arrived,
            )
            db.add(inbound)

            if status in ["contacted", "replied", "booked", "lost"]:
                template = REPLY_TEMPLATES[thread_count % len(REPLY_TEMPLATES)]
                sent = arrived + timedelta(seconds=random.uniform(2.5, 5.0))
                latency_ms = int((sent - arrived).total_seconds() * 1000)
                body = template["body"].format(
                    first_name=lead.first_name,
                    company=lead.organization.name if lead.organization else "your agency",
                )
                outbound = EmailMessage(
                    id=uuid4(), thread_id=thread.id,
                    gmail_message_id=f"msg-seed-out-{thread_count}",
                    direction="outbound", from_email="asdr.demo@gmail.com",
                    to_email=email, subject=f"Re: {thread.subject}",
                    body_text=body, intent=None, intent_confidence=None,
                    reply_latency_ms=latency_ms, arrived_at=None, sent_at=sent,
                    created_at=sent,
                )
                db.add(outbound)

            thread_count += 1

        # Add more threads for variety
        while thread_count < 30:
            lead = random.choice(list(leads.values()))
            if lead.status == "captured" or lead.status == "no_show":
                continue
            gmail_tid = f"thread-seed-{thread_count}"
            subjects = [
                "Interested in your platform", "Pricing question", "Can we schedule a demo?",
                "Not the right time", "Partnership opportunity", "Tell me more about ASDR",
            ]
            thread = EmailThread(
                id=uuid4(), lead_id=lead.id, gmail_thread_id=gmail_tid,
                subject=random.choice(subjects), status="open",
            )
            db.add(thread)
            arrived = _rand_time(random.randint(1, 13))
            inbound = EmailMessage(
                id=uuid4(), thread_id=thread.id,
                gmail_message_id=f"msg-seed-in-{thread_count}",
                direction="inbound", from_email=lead.email,
                to_email="asdr.demo@gmail.com", subject=thread.subject,
                body_text="Hi, I'm interested in learning more about your services.",
                intent=random.choice(INTENTS[:3]), intent_confidence=random.uniform(0.7, 0.99),
                reply_latency_ms=None, arrived_at=arrived, sent_at=arrived,
                created_at=arrived,
            )
            db.add(inbound)

            template = REPLY_TEMPLATES[thread_count % len(REPLY_TEMPLATES)]
            sent = arrived + timedelta(seconds=random.uniform(2.5, 5.5))
            latency_ms = int((sent - arrived).total_seconds() * 1000)
            body = template["body"].format(
                first_name=lead.first_name,
                company=lead.organization.name if lead.organization else "your agency",
            )
            outbound = EmailMessage(
                id=uuid4(), thread_id=thread.id,
                gmail_message_id=f"msg-seed-out-{thread_count}",
                direction="outbound", from_email="asdr.demo@gmail.com",
                to_email=lead.email, subject=f"Re: {thread.subject}",
                body_text=body, intent=None, intent_confidence=None,
                reply_latency_ms=latency_ms, arrived_at=None, sent_at=sent,
                created_at=sent,
            )
            db.add(outbound)
            thread_count += 1

        # --- Meetings (8) ---
        print("Seeding meetings...")
        booked_leads = [l for l in leads.values() if l.status == "booked"]
        for i, lead in enumerate(booked_leads[:4]):
            mtime = _rand_time(random.randint(1, 14))
            meeting = Meeting(
                id=uuid4(), lead_id=lead.id, source=random.choice(["email", "chatbot"]),
                google_event_id=f"gcal-seed-{i}",
                title=f"ASDR Demo with {lead.first_name}",
                start_at=mtime, end_at=mtime + timedelta(minutes=30),
                hangout_link="https://meet.google.com/abc-defg-hij",
                status="confirmed" if i < 3 else "completed",
                created_at=mtime, updated_at=mtime,
            )
            db.add(meeting)

        # 4 more meetings (1 cancelled, 3 confirmed)
        for i in range(4, 8):
            lead = random.choice(list(leads.values()))
            mtime = _rand_time(random.randint(1, 14))
            meeting = Meeting(
                id=uuid4(), lead_id=lead.id, source=random.choice(["email", "chatbot", "manual"]),
                google_event_id=f"gcal-seed-{i}",
                title=f"Strategy Call — {lead.first_name} {lead.last_name}",
                start_at=mtime, end_at=mtime + timedelta(minutes=30),
                hangout_link="https://meet.google.com/xyz-uvwx-yz",
                status="confirmed" if i < 7 else "cancelled",
                created_at=mtime, updated_at=mtime,
            )
            db.add(meeting)

        # --- Chat Sessions (18) ---
        print("Seeding chat sessions...")
        for i in range(18):
            lead = random.choice(list(leads.values()))
            state = random.choice(CHAT_STATES[:5])  # GREETING → BOOK
            session = ChatSession(
                id=uuid4(), lead_id=lead.id, state=state,
                proposed_slots=[], retry_count=random.randint(0, 2),
                created_at=_rand_time(random.randint(1, 14)),
                updated_at=_rand_time(random.randint(0, 7)),
            )
            db.add(session)
            await db.flush()

            msgs = []
            if state == "GREETING":
                msgs = [
                    ("inbound", "Hi, I want to learn about ASDR."),
                    ("outbound", "Hello! I'd love to tell you more. Are you looking to automate your outbound sales?"),
                ]
            elif state in ["INTENT_CONFIRM", "PROPOSE_TIMES", "CONFIRM"]:
                msgs = [
                    ("inbound", "Hi, I want to learn about ASDR."),
                    ("outbound", "Hello! I'd love to tell you more. Are you looking to automate your outbound sales?"),
                    ("inbound", "Yes, we need help with lead generation."),
                    ("outbound", "Great! Let me suggest a few times for a demo. How about:"),
                ]
            elif state in ["BOOK", "DONE"]:
                msgs = [
                    ("inbound", "Hi, I want to learn about ASDR."),
                    ("outbound", "Hello! I'd love to tell you more."),
                    ("inbound", "Yes, we need help with lead generation."),
                    ("outbound", "Here are 3 times:"),
                    ("inbound", "Wednesday at 3 PM works."),
                    ("outbound", "Confirmed! Meeting booked. Here's your link: https://meet.google.com/demo"),
                ]
            for direction, text in msgs:
                db.add(ChatMessage(
                    id=uuid4(), session_id=session.id,
                    direction=direction, text=text,
                    created_at=_rand_time(random.randint(1, 13)),
                ))

        # --- Activity Events (~600) ---
        print("Seeding activity events...")
        events = []
        for day_offset in range(14):
            day = NOW - timedelta(days=day_offset)
            count = random.randint(35, 50)  # ~42/day avg = ~588 total
            for _ in range(count):
                lead = random.choice(list(leads.values()))
                etype = random.choice(ACTIVITY_TYPES)
                payload = {}
                if etype == "email_inbound":
                    payload = {"from": lead.email, "subject": "Demo inquiry", "intent": random.choice(INTENTS[:3])}
                elif etype == "email_outbound":
                    payload = {"to": lead.email, "reply_latency_ms": random.randint(2000, 5000)}
                elif etype == "meeting_booked":
                    payload = {"title": f"Demo with {lead.first_name}", "time": _rand_time(day_offset).isoformat()}
                elif etype == "lead_status_change":
                    payload = {"from": random.choice(STATUSES), "to": lead.status}
                events.append(ActivityEvent(
                    type=etype, lead_id=lead.id,
                    payload=payload,
                    created_at=day.replace(hour=random.randint(0, 23), minute=random.randint(0, 59)),
                ))

        # Sort by time so sparkline looks natural
        events.sort(key=lambda e: e.created_at)
        for e in events:
            db.add(e)

        # --- Demo Metrics Cache ---
        print("Computing metrics cache...")
        await db.flush()

        # Count from what we just seeded
        leads_count = len(leads_data)
        meetings_count = 8
        outbound_msgs = [e for e in db.new if isinstance(e, EmailMessage) and e.direction == "outbound"]
        outbound_count = len(outbound_msgs)
        latencies = [m.reply_latency_ms for m in outbound_msgs if m.reply_latency_ms]
        avg_latency = int(sum(latencies) / len(latencies)) if latencies else 3700
        est_hours = meetings_count * 0.75 + outbound_count * 0.25
        est_cost = est_hours * 60
        success_rate = meetings_count / max(leads_count, 1)

        cache = DemoMetricsCache(
            id=1, leads_count=leads_count, meetings_count=meetings_count,
            est_cost_saved=est_cost, est_hours_saved=est_hours,
            avg_reply_latency_ms=avg_latency, success_rate=success_rate,
        )
        db.add(cache)

        # --- KV ---
        from models import KV
        db.add(KV(key="gmail_last_history_id", value="0"))

        await db.commit()
        print(f"Seeded: {leads_count} leads, 30+ threads, 8 meetings, 18 chat sessions, ~{len(events)} activity events")


if __name__ == "__main__":
    asyncio.run(seed())
