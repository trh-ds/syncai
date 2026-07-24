# ASDR — Autonomous SDR & Ops Router

A B2B SaaS MVP that automates inbound email triage, lead qualification, AI-drafted replies, live chatbot conversations, and meeting booking — reducing a 10-person ops team to a single monitor.

---

## Architecture Overview

```
Inbound Email (Gmail)
      │
      ▼
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│  Lead Filter    │────▶│  Triage LLM  │────▶│  Draft LLM   │
│  (skip bounces) │     │  (Groq)      │     │  (Groq)      │
└─────────────────┘     └──────┬───────┘     └──────┬───────┘
                               │                     │
                               ▼                     ▼
                        ┌──────────────┐     ┌──────────────┐
                        │  ChromaDB    │     │  Draft Reply │
                        │  RAG (KB)    │     │  + Chatbot   │
                        └──────────────┘     │  CTA         │
                                             └──────┬───────┘
                                                    │
                              ┌─────────────────────┼──────────────┐
                              ▼                     ▼              ▼
                     ┌──────────────┐       ┌──────────┐   ┌───────────┐
                     │  Postgres    │       │  Inbox   │   │  Chatbot  │
                     │  (Customers, │       │  Dashbd  │   │  /chat    │
                     │   Emails,    │       │  Approve │   │  Qualify  │
                     │   Meetings)  │       │  / Send  │   │  + Book   │
                     └──────────────┘       └──────────┘   └───────────┘
```

---

## Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Frontend** | Next.js 16 (App Router), React 19, TypeScript, Tailwind v4, Shadcn UI | Per project blueprint |
| **Backend** | Python 3.12, FastAPI, Uvicorn | Per project blueprint |
| **LLM** | Groq (`llama-3.3-70b-versatile`), raw `groq` SDK | 3 prompt calls don't justify LangChain |
| **Vector DB** | ChromaDB, in-process, persisted to disk | No external account needed, one mock KB |
| **RDBMS** | PostgreSQL 16, SQLAlchemy 2.x + `psycopg[binary]` | ORM + DB are a pair, not alternatives |
| **Email** | Gmail API (OAuth 2.0) — read, send, modify | Real inbox monitoring + reply |
| **Calendar** | Google Calendar API (free/busy, events) | Availability check + booking |
| **Auth** | None (single-tenant demo) | MVP scope; multi-tenancy is Phase 5 |
| **Deployment** | Docker + docker-compose, GitHub Actions, Vercel (frontend), Render (backend) | Per project blueprint |

---

## Features

### 1. Gmail Mail Bot
- Polls your Gmail inbox every 30 seconds for unread emails
- **Pre-filter**: Only `mailer-daemon@`, `bounce@`, `postmaster@`, `auto-reply@` are skipped — real people (even from gmail/outlook) always go through
- **Triage**: Groq LLM classifies intent (Sales/Support/Spam/Other), extracts sender name, writes 1-sentence summary, evaluates lead quality, and decides whether a draft is needed
- **RAG**: ChromaDB retrieves relevant knowledge base context (pricing, case studies, policies)
- **Draft**: Groq LLM writes a personalized reply ending with a CTA directing the lead to the chatbot for faster answers and booking
- **Two modes**:
  - **HITL (Human-in-the-Loop)**: Drafts appear in the dashboard for approval, approval sends the reply via Gmail
  - **Auto**: Reply sent immediately, moves to "sent" tab
- **Toggle**: Switch Auto/HITL live from the dashboard header
- **Deduplication**: Uses Gmail message IDs to avoid reprocessing
- **Rate limit handling**: If Groq rate limit is hit, emails stay unread and retry when the limit resets

### 2. AI Chatbot (/chat)
- Live chat UI for website visitors
- Accepts message + optional email/name
- Groq LLM with full context (knowledge base + customer history + calendar availability)
- **Lead qualification**: Automatically scores leads as Hot / Warm / Cold based on conversation signals
- **Knowledge base aware**: Answers questions about services, pricing, process from ChromaDB
- **Direct answering**: Handles FAQs, negotiations, and service comparisons
- **Meeting booking**: When a customer wants to book, the chatbot:
  1. Checks Google Calendar availability
  2. Books the first available slot
  3. Sends a confirmation email via Gmail
  4. Upgrades lead score to "Hot"
- **Shared memory**: Chatbot and mail bot share the same customer database — the email conversation history is visible to the chatbot and vice versa

### 3. CRM Dashboard (/crm)
- **Lead Pipeline**: Visual breakdown of Hot / Warm / Cold leads with horizontal bar charts
- **Service Breakdown**: Keyword-classified inquiry types (Web Design, SEO, Marketing, Development, Consulting, Other)
- **Source Tracking**: Leads broken down by source (email vs chat)
- **Conversion Rate**: Percentage of leads that booked meetings
- **Activity Feed**: Real-time timeline combining emails, chat messages, and booked meetings
- **Refresh button**: Manual refresh of all stats

### 4. Calendar & Booking
- Google Calendar API integration (same OAuth as Gmail)
- **Availability**: Checks free/busy for 30-min slots during work hours (9am–5pm Mon–Fri) for the next 7 days
- **Booking**: Creates Google Calendar events with attendee, sends email updates
- **Conflict detection**: Skips busy slots, only returns available times
- **Confirmation email**: Auto-sent via Gmail after booking with date/time details

### 5. Demo Page (/demo)
- Public pitch page: paste a company URL + sample email
- Backend scrapes the URL for context, runs Groq draft pipeline
- Returns the drafted reply and the scraped context
- Nothing persisted — safe for demos

### 6. API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/webhooks/email` | Ingest email → triage → RAG → draft → persist (201) |
| `GET` | `/api/v1/emails?status=` | List emails (filterable: pending/approved/discarded/sent) |
| `GET` | `/api/v1/emails/{id}` | Get single email |
| `PATCH` | `/api/v1/emails/{id}` | Edit draft / transition status |
| `POST` | `/api/v1/demo/run` | Scrape URL → draft reply (no persist) |
| `GET` | `/api/v1/settings` | Get mail mode, poll interval, Gmail status |
| `PATCH` | `/api/v1/settings` | Toggle auto/hitl mode |
| `POST` | `/api/v1/chat/message` | Chat message → reply + lead score + booking |
| `GET` | `/api/v1/calendar/availability` | Available 30-min booking slots |
| `POST` | `/api/v1/calendar/book` | Book a meeting |
| `GET` | `/api/v1/crm/stats` | CRM aggregate statistics (incl. pipeline forecast) |
| `GET` | `/api/v1/crm/activity` | Recent CRM activity feed |
| `GET` | `/api/v1/onboarding/status` | Org Gmail status (auth) |
| `GET` | `/api/v1/onboarding/google` | Start Gmail+Calendar OAuth (auth) |
| `GET` | `/api/v1/onboarding/google/callback` | OAuth callback → store refresh token |
| `POST` | `/api/v1/unsubscribe/{token}` | CAN-SPAM opt-out (also GET for one-click email links) |

### 7. SaaS Shell (auth, multi-tenant-lite)
- **Auth**: Supabase Auth — email/password + Google OAuth on `/signup`, `/login`
- **Multi-tenant-lite**: `org_id` on emails/customers/interactions/meetings; every query filters by it. Unauthenticated traffic falls back to a default org (keeps the demo working with zero config)
- **Onboarding** (`/onboarding`): sign up, connect Gmail+Calendar via OAuth UI (replaces the manual `scripts/gmail_auth.py` run)

### 8. Compliance (CAN-SPAM)
- Every AI-drafted email gets an auto-appended footer: business name, physical address, one-click unsubscribe link
- `customers.opted_out` is a hard gate — poller and all send paths skip opted-out contacts, no exceptions
- `consent_source` / `consent_timestamp` tracked on every customer
- `send_logs` table records the exact disclosure text + timestamp of every send (audit trail)

### 9. Agent Upgrades
- **Reply triage**: replies to engaged threads are classified separately (interested / not-now / referral / objection / unsubscribe) and routed — unsubscribe auto-opts-out, interested marks hot + drafts follow-up
- **Enrichment agent**: Apollo.io per-lead lookup (job title, company size) on new customers — Scale plan only
- **Slack**: incoming webhook fires on new hot leads and booked meetings — Growth plan and up
- **Pipeline forecast**: `deal_value_estimate` per customer (stage heuristic), stage-weighted forecast on `/crm`

---

## Database Schema

### Table: `organizations`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | TEXT | |
| owner_user_id | UUID NULL UNIQUE | Supabase auth user (NULL = default demo org) |
| owner_email | TEXT NULL | |
| gmail_refresh_token | TEXT NULL | Set via onboarding OAuth |
| gmail_user_email | TEXT NULL | |
| created_at | TIMESTAMPTZ | |

### Table: `emails`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| org_id | UUID NULL | Tenant scope |
| sender | TEXT | From-address |
| sender_name | TEXT NULL | Extracted by triage |
| subject | TEXT | |
| body | TEXT | |
| intent | TEXT | Sales / Support / Spam / Other |
| summary | TEXT | 1-sentence triage summary |
| ai_draft | TEXT NULL | Null for non-sales emails |
| status | TEXT | pending / approved / discarded / sent |
| gmail_message_id | TEXT UNIQUE | Dedup key |
| gmail_thread_id | TEXT NULL | Gmail thread tracking |
| reply_intent | TEXT NULL | interested / not-now / referral / objection / unsubscribe |
| created_at | TIMESTAMPTZ | Indexed DESC |
| updated_at | TIMESTAMPTZ | Auto-updated |

### Table: `customers`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| org_id | UUID FK NULL | Tenant scope |
| email | TEXT UNIQUE | |
| name | TEXT NULL | |
| lead_score | TEXT | hot / warm / cold |
| source | TEXT | email / chat |
| consent_source | TEXT NULL | inbound_email / chat |
| consent_timestamp | TIMESTAMPTZ NULL | CAN-SPAM consent record |
| opted_out | BOOLEAN | Hard send gate when true |
| unsubscribe_token | TEXT UNIQUE | One-click unsubscribe |
| deal_value_estimate | DOUBLE NULL | Stage heuristic (hot 5000 / warm 2000 / cold 500) |
| job_title | TEXT NULL | Apollo enrichment |
| company_size | TEXT NULL | Apollo enrichment |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### Table: `interactions`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| org_id | UUID FK NULL | Tenant scope |
| customer_id | UUID FK | |
| channel | TEXT | email / chat |
| content | TEXT | Message body |
| direction | TEXT | inbound / outbound |
| created_at | TIMESTAMPTZ | |

### Table: `meetings`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| org_id | UUID FK NULL | Tenant scope |
| customer_id | UUID FK NULL | |
| google_event_id | TEXT NULL | |
| summary | TEXT | |
| start_time | TIMESTAMPTZ | |
| end_time | TIMESTAMPTZ | |
| status | TEXT | scheduled / cancelled |
| created_at | TIMESTAMPTZ | |

### Table: `send_logs`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| org_id | UUID NULL | Tenant scope |
| recipient | TEXT | |
| disclosure_text | TEXT | Exact CAN-SPAM footer sent |
| sent_at | TIMESTAMPTZ | Audit trail |

### Vector Store: ChromaDB
- Collection: `knowledge_base`
- Persistence: Disk volume (`/data/chroma`)
- Seeded at startup from `mock_kb.txt` if empty
- Retrieved for every Sales/Support email and chat query

---

## Folder Structure

```
syncai/
├── .github/workflows/ci.yml     # CI pipeline
├── docker-compose.yml           # Local dev orchestration
├── render.yaml                  # Render Blueprint deploy
│
├── backend/
│   ├── main.py                  # FastAPI app entry, lifespan, routes
│   ├── agents/
│   │   ├── triage_agent.py      # Groq triage + ICP filtering
│   │   ├── rag_agent.py         # ChromaDB retrieval
│   │   └── draft_agent.py       # Groq draft + chatbot CTA
│   ├── api/v1/
│   │   ├── webhooks.py          # POST /webhooks/email
│   │   ├── endpoints.py         # GET/PATCH emails, demo
│   │   ├── settings.py          # GET/PATCH settings
│   │   ├── chat.py              # POST /chat/message + booking
│   │   ├── calendar_routes.py   # Calendar availability + book
│   │   └── crm.py               # CRM stats + activity
│   ├── services/
│   │   ├── gmail_client.py      # Gmail API (read, send, modify)
│   │   ├── mail_poller.py       # Async 30s inbox poller
│   │   ├── lead_filter.py       # Bounce/auto-reply pre-filter
│   │   ├── calendar_service.py  # Google Calendar free/busy + events
│   │   └── customer_service.py  # Customer CRUD + interaction log
│   ├── models/
│   │   ├── email.py             # SQLAlchemy Email + Pydantic schemas
│   │   └── customer.py          # Customer, Interaction, Meeting models
│   ├── core/
│   │   ├── config.py            # Pydantic settings (env vars)
│   │   └── database.py          # SQLAlchemy engine + session
│   ├── scripts/
│   │   └── gmail_auth.py        # One-time OAuth script
│   ├── mock_kb.txt              # Seed data for ChromaDB
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Landing page
│   │   ├── dashboard/page.tsx   # Inbox Kanban + mode toggle
│   │   ├── chat/page.tsx        # AI chatbot widget
│   │   ├── crm/page.tsx         # CRM analytics dashboard
│   │   └── demo/page.tsx        # Public demo page
│   ├── components/
│   │   ├── Navbar.tsx           # Top navigation
│   │   ├── EmailCard.tsx        # Email card with edit/approve/discard
│   │   └── ui/                  # Shadcn UI primitives
│   ├── lib/
│   │   └── api.ts               # Typed fetch wrapper for all endpoints
│   ├── package.json             # Next.js 16, React 19, Tailwind 4
│   ├── Dockerfile
│   └── tsconfig.json
│
├── .env.example                 # Root env template
└── README.md
```

---

## Environment Variables

### Backend (`backend/.env`)
| Variable | Default | Required |
|---|---|---|
| `GROQ_API_KEY` | — | Yes |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | No |
| `DATABASE_URL` | `postgresql+psycopg://...` | No |
| `CLIENT_COMPANY_NAME` | `Apex Digital` | No |
| `CHROMA_PATH` | `./chroma_data` | No |
| `KB_SEED_FILE` | `./mock_kb.txt` | No |
| `CORS_ORIGINS` | `http://localhost:3000` | No |
| `GMAIL_CLIENT_ID` | — | For Gmail polling |
| `GMAIL_CLIENT_SECRET` | — | For Gmail polling |
| `GMAIL_REFRESH_TOKEN` | — | For Gmail polling |
| `GMAIL_USER_EMAIL` | — | For Gmail polling |
| `MAIL_MODE` | `hitl` | No |
| `MAIL_POLL_INTERVAL` | `30` | No |
| `CHATBOT_URL` | `http://localhost:3000/chat` | No |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_JWT_SECRET` | — | For auth (multi-tenant) |
| `SLACK_WEBHOOK_URL` | — | For Slack alerts |
| `APOLLO_API_KEY` | — | For lead enrichment |
| `BUSINESS_NAME` / `BUSINESS_ADDRESS` | Apex Digital LLC / Austin TX | CAN-SPAM footer |
| `PUBLIC_API_URL` / `WEB_URL` | localhost | Unsubscribe links / redirects |

### Frontend (`frontend/.env.local`)
| Variable | Example | Required |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Yes |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://xxx.supabase.co` | For auth |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `eyJ...` | For auth |

---

## Setup & Quickstart

### Local Development
```bash
cp .env.example .env                    # Root env for docker-compose
cp backend/.env.example backend/.env    # Backend env
# Fill in GROQ_API_KEY in backend/.env
docker compose up --build
```
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

### Gmail Setup

**Self-serve (product path):** sign up at `/signup` → `/onboarding` → "Connect Google account".
Requires a **Web application** OAuth client with redirect URI
`{PUBLIC_API_URL}/api/v1/onboarding/google/callback` registered in Google Cloud Console.

**Manual (single-tenant demo path):**
1. Google Cloud Console → create project → enable Gmail API + Calendar API
2. Credentials → OAuth 2.0 Client ID (Desktop app)
3. Set `GMAIL_CLIENT_ID` and `GMAIL_CLIENT_SECRET` in `backend/.env`
4. Run `python backend/scripts/gmail_auth.py` → authorise in browser
5. Copy refresh token to `GMAIL_REFRESH_TOKEN` in `backend/.env`
6. Set `GMAIL_USER_EMAIL=your.email@gmail.com`

### Environment Setup
```bash
cp .env.example .env                      # Root env
cp backend/.env.example backend/.env      # Backend env
cp frontend/.env.example frontend/.env.local  # Frontend env
```

---

## Deployment

### Backend (Render)
- Use `render.yaml` Blueprint → creates `asdr-backend` (Docker web service only)
- **Database + Auth are on Supabase** (Render's free Postgres auto-expires ~30–90 days) — see DEPLOY.md
- Manually set: `GROQ_API_KEY`, `DATABASE_URL` (Supabase), `SUPABASE_*`, `CORS_ORIGINS`, Gmail/Slack/Apollo keys
- Keep-alive: `.github/workflows/keepalive.yml` pings `/health` every 3 days (prevents Supabase auto-pause + Render sleep)

### Frontend (Vercel)
- Import repo → set Root Directory to `frontend`
- Set `NEXT_PUBLIC_API_URL` to Render backend URL

### CI/CD
GitHub Actions on push to `main`:
- Python compile + import check
- `npm lint` + `npm build`
- Docker build smoke test

---

## Zero-Dollar Cost Design

Every feature was designed to operate within **$0/month** operating costs:

| Cost Centre | Solution | Monthly Cost |
|---|---|---|
| **LLM** | Groq free tier (100K tokens/day) — enough for ~50 leads/day at current usage | $0 |
| **Database + Auth** | Supabase free tier (500 MB DB, 50k MAU, 2 projects) — keep-alive cron prevents 7-day auto-pause | $0 |
| **Vector DB** | ChromaDB in-process (no external service) | $0 |
| **Hosting (frontend)** | Vercel free tier | $0 |
| **Hosting (backend)** | Render free web service (sleeps after 15 min idle, ~60s cold start) | $0 |
| **Notifications** | Slack incoming webhook | $0 |
| **Enrichment** | Apollo.io free credits — light per-lead lookups only | $0 |
| **Email API** | Gmail free tier (Google OAuth, no paid API) | $0 |
| **Calendar API** | Google Calendar free tier | $0 |
| **CI/CD** | GitHub Actions free tier (2000 min/month) | $0 |
| **Container Registry** | Docker Hub free | $0 |
| **Total** | | **$0** |

### Upcoming Features (also $0 cost baked in)
- **Gmail webhook (push instead of poll)**: Using Google Cloud Pub/Sub free tier — replaces polling, reduces latency
- **Slack notifications**: Slack webhooks are free
- **HubSpot CRM sync**: Using free tier API actions
- **Multi-tenant support**: Row-level security (no extra infra cost)
- **Analytics dashboard**: Built on existing Postgres queries — no external analytics service
- **Email templates**: Stored in Postgres text columns — no email service provider
- **File attachments for demo context**: Stored in Postgres binary columns or free tier cloud storage
- **Lead scoring webhook**: Outbound webhooks to customer's CRM (no external scoring service)
- **In-app notifications**: Using browser Notification API (no push service)
- **Rate limit queuing**: In-memory queue backed by Postgres (no Redis needed)

---

## ICP (Ideal Customer Profile)

The triage agent and chatbot are configured for a **Digital Marketing Agency** target:

**In Scope (our ICP):**
- SMBs, startups, and mid-market companies (10–200 employees)
- Looking for: SEO, PPC, social media marketing, content marketing, email marketing, web design, branding, advertising
- Has budget + timeline + specific pain point

**Out of Scope (not our ICP):**
- Job seekers and applicants
- Automated system notifications (AWS, Google, security alerts)
- Newsletters, promotional emails, product announcements
- SaaS trial notifications
- Social media notifications
- E-commerce marketing emails
- Invoice/billing/payment reminders

---

## Key Design Decisions

1. **No LangChain**: Three prompt calls don't justify the dependency weight at MVP scale
2. **No Pinecone**: ChromaDB runs in-process; no external API key or account needed
3. **Single tenant**: Login + multi-tenancy is post-sale work
4. **Mocked email sending**: "Approve & Send" only flips status in MVP; real sending uses Gmail API
5. **Mutable settings singleton**: Fine for single-tenant; would use Redis/DB for multi-tenant
6. **Pre-filter before LLM**: Saves tokens by skipping obvious machine-generated emails
7. **Deduplication via Gmail message ID**: Prevents processing the same email twice
8. **Rate limit backpressure**: Emails stay unread on 429; retried automatically when limit resets
