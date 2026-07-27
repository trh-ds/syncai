# ASDR Demo Build — Execution Brief for DeepSeek

> **Executor (DeepSeek): read everything below before typing a single line. Follow steps in §10 in order. Do not improvise features that aren't here. Do not skip validation in §11. Assumptions are flagged inline with `ASSUMPTION:`.**

## Stack locked for this demo (do not deviate)
- Frontend: Next.js 16 (App Router), React 19, TypeScript, Tailwind v4, Shadcn UI (`@shadcn/ui` CLI).
- Backend: FastAPI, Python 3.12, Uvicorn single worker (localhost only).
- LLM: Groq only. Two models (per owner decision):
  - Triage/classify → `llama-3.1-8b-instant` (fast first-token).
  - Draft reply / chatbot turns → `llama-3.3-70b-versatile` (quality).
- RAG: ChromaDB (embedded sqlite client for localhost — no separate server, no docker for Chroma).
- DB: PostgreSQL 16 + SQLAlchemy 2.0 (async). Local Postgres on laptop.
- Mail/Calendar: Gmail API + Google Calendar API (single OAuth client).
- Apollo: Apollo People Search API (REST).
- Runtime: **localhost on Tirth's laptop**. Backend `http://localhost:8000`, frontend `http://localhost:3000`. OAuth redirect URIs are `http://localhost:8000/...` only.
- Budget: $0. Free tiers throughout.
- **Greenfield build.** Ignore earlier repo design (Supabase, Stripe, etc.) — those were removed on purpose.

## 1. Architecture

- Single repo at project root, monorepo-lite:
  - `/backend`  — FastAPI app, Python. Owns Gmail/Calendar/Apollo/Groq/DB/Chroma. Exposes REST + SSE.
  - `/frontend` — Next.js app. Consumes backend REST + SSE. Pure UI, no server-side data fetching of external APIs.
- Build/run: one `docker-compose.yml` is **optional** — owner is running on localhost; default `Makefile` targets `make backend` / `make frontend` run uvicorn + next dev directly. (Leave compose file present but not required to use.)
- Two processes is the whole topology. No queue, no Redis, no Pub-Sub broker. `ponytail: this is single-laptop, no-concurrency demo; per-lead locks stay out of scope until throughput matters.`
- Demo corners cut (explicit, non-prod):
  - No worker pool — one Gmail poller coroutine inside FastAPI app via `asyncio.create_task`.
  - Secrets in `.env` (gitignored). No vault, no KMS.
  - OAuth refresh token stored in `.env`; no per-user multi-tenant OAuth graph. One monitored inbox only.
  - CORS wide open to `localhost:3000`.
  - No rate-limiting, no input sanitization beyond basic, no auth on backend.
  - ChromaDB embedded, not cluster.
  - No automated tests beyond the boot self-check in §11.
- Anything NOT in this list and NOT in the build checklist (§10) is out of scope. Do not build it.

## 2. Gmail pipeline (pure polling, list/history + messages.get)

**Mechanism:** poll loop every **1.5 s** (demo-tuned; tunable via `GMAIL_POLL_INTERVAL_MS`). Use Gmail Users History API, not message re-listing.

**Latency budget end-to-end (target < 4.0 s):**
| Stage | Mean | Worst | Notes |
|---|---|---|---|
| Poll cadence jitter | 0.75 s | 1.5 s | 1.5 s interval → avg half |
| `users.history.list` (startHistoryId) | 0.25 s | 0.6 s | returns added messages since last id |
| `users.messages.get` (batch by id, format=full) | 0.5 s | 1.0 s | fetch headers + payload |
| Groq 8b triage/classify | 0.3 s | 0.6 s | one short prompt |
| Insert lead/thread/message into Postgres + Chroma | 0.05 s | 0.15 s | |
| Groq 70b draft reply | 1.2 s | 1.8 s | ~150 tokens, non-streamed |
| Gmail `messages.send` (raw MIME) | 0.4 s | 0.8 s | direct send, no draft step |
| **Total** | **~3.45 s** | **~6.45 s** | worst case exceeds budget; acceptable for demo, see note |

**Noting the worst case:** pure polling can miss the 4 s target on a cold first poll or a slow Groq call. Demo mitigation: poll interval set to 1.5 s, and drop draft to `llama-3.1-8b-instant` if `GROQ_MODEL_DRAFT_FAST_FALLBACK=true` env var is set (off by default). Owner will tune live in §11. `ponytail: pure polling has a 1.5s ceiling per cycle; if sub-4s shows flaky on the dry-run, switch draft model via env, no code change.`

**OAuth scopes (monitored inbox only):**
- `https://www.googleapis.com/auth/gmail.modify` (read + send, not full gmail.send-only combo — modify covers read/send/labels).
- `https://www.googleapis.com/auth/calendar.events`
- `openid email profile` (userinfo).

**Credential storage:**
- Single Google OAuth "Web application" client in GCP project, **publishing status = "Testing"**, both Gmail accounts (monitored + a throwaway used as prospect) added as **test users**.
- First-run: backend route `GET /auth/start` → Google consent → `GET /auth/callback` → exchanges code for refresh + access → writes the refresh token to `.env` as `GMAIL_REFRESH_TOKEN` (or a local `secrets.json` gitignored). After first run, poller uses refresh token to mint access tokens (auto-refresh on 401).
- `ASSUMPTION:` Tirth will pre-run `/auth/start` once before the call so refresh token is on disk; do not assume the live consent screen will work mid-call.

**Poller loop (DeepSeek: implement exactly):**
1. Load refresh token from env, mint access token (cache until expiry).
2. Maintain `last_history_id` in DB state row (`kv` table, key `gmail_last_history_id`).
3. Every `GMAIL_POLL_INTERVAL_MS`: call `users.history.list` with `startHistoryId=<last>`, `labelId=INBOX`.
4. For each `messageAdded` in history → `users.messages.get(id, format=full)`.
5. Skip if `message.id` already exists in `email_messages` (idempotent).
6. Skip if message `From` equals monitored inbox (don't reply to self).
7. Classify by Groq 8b (triage prompt: output JSON `{intent: book|question|objection|spam|oob, lead_email, lead_name, summary}`).
8. If `intent in {book, question, objection}` → draft reply with Groq 70b → `users.messages.send` with `In-Reply-To` + `References` headers (Thread ID) so it threads in Gmail UI.
9. Persist lead (upsert by email), thread, message (both incoming + sent), activity_event.
10. Update `last_history_id` to the history list response's `historyId`.

## 3. Chatbot / negotiation flow

The chatbot is a **separate live-chat widget** (not email). Email answers promise #1 (4 s reply); chatbot answers promise #2 (negotiate + book). Both feed the same dashboard.

- Route: `/demo/chat` on frontend. One fixed demo lead id (`env: DEMO_LEAD_ID`, seeded). Prospect = Parth (or Tirth acting as prospect in a second tab).
- Backend endpoint `POST /api/chat/message` body `{lead_id, text}` → returns `{reply, state, proposed_times?, booked_meeting?}`.
- Backend maintains a per-lead state row in `chat_sessions` table.

**State machine:**
```
GREETING
  → INTENT_CONFIRM   (bot confirms prospect wants a meeting)
  → PROPOSE_TIMES    (bot offers 3 slots from a configurable window)
      branch BUSY/LATER/OBJECTION → re-enter PROPOSE_TIMES (window shifted ±N days, max 3 retries)
      branch ACCEPT → CONFIRM
  → CONFIRM          (bot states chosen slot, asks "Confirm?")
      branch NO → PROPOSE_TIMES
      branch YES → BOOK
  → BOOK             (backend calls Google Calendar insert; on success → DONE)
  → DONE             (bot returns meet link + meeting id)
  terminal LOST      (any explicit "no thanks"/stop, or 3 failed PROPOSE_TIMES)
```

**Slot selection:** slots come from a configurable working-hours window (`CHAT_WORKING_HOURS=09:00-18:00`, `CHAT_TZ=Asia/Kolkata`) and avoid booked meetings already in the DB. Slots are pre-generated for the next 5 working days, 3 at a time.

**Pushback handling:** the Groq 70b turn prompt includes the state + last user message + instruction: classify user response as `accept | propose_alt | decline | question`. If `propose_alt` → bot generates 3 new slots in next/prev window, state stays PROPOSE_TIMES. If `decline` → LOST, lead status = `lost`, dashboard reflects it.

**On BOOK:** synchronous backend call to Google Calendar (§4). On success: insert into `meetings` table, update `lead.status = 'booked'`, push `activity_event` (type=`meeting_booked`) → dashboard live feed → calendar view refresh on next poll.

**No live transcription, no voice.** Text only. (Corner cut, flagged.)

## 4. Calendar integration

- Reuse the same monitored-inbox OAuth refresh token (since OAuth client requests both `gmail.modify` + `calendar.events` scopes in one consent).
- Calendar ID = `primary` of monitored inbox (override via `GOOGLE_CALENDAR_ID`).
- **Create:** `POST /api/meetings/book` (called by chatbot BOOK state and also exposed for manual test) → Google Calendar `events.insert` with:
  - `start`/`end` `{dateTime, timeZone}`
  - `attendees: [{email: monitored}, {email: prospect}]`
  - `conferenceData` request → returns `hangoutLink`. `sendUpdates: 'all'` so both Gmails get the invite.
- **Read for dashboard:** backend endpoint `GET /api/meetings` returns merged from local `meetings` table (single source of truth — Google is source, local is the display copy). Near-real-time: frontend Calendar page polls `/api/meetings` every 3 s. (No SSE for calendar; SSE is reserved for the activity feed, see §7.)
- **Real-time reflection:** the moment BOOK succeeds, the meetings row is inserted and the next Activity-feed SSE event of type `meeting_booked` pushes the new meeting object inline so Parth sees it appear without a refresh.

## 5. Apollo integration

- One endpoint `POST /api/leads/sync-apollo` and `GET /api/leads/sync-apollo/status`.
- Calls Apollo People Search (`POST https://api.apollo.io/v1/people/search`? — `ASSUMPTION:` use the documented endpoint; verify exact path by hitting Apollo's API docs once during build). Headers: `X-Api-Key: <APOLLO_API_KEY>`, body uses `person_titles` / `organization_num_employees_ranges` / `q_organization_keyword` from env `APOLLO_SAVED_QUERY_JSON`.
- Response → map each `people[]` to `leads` row:
  - `first_name`, `last_name`, `email`, `title`, `organization.name`, `organization.industry`, `organization.employee_count`, `linkedin_url`, `apollo_person_id`, `source='apollo'`, `status='captured'`, `enriched_data` JSONB.
- Status pipeline tracked per lead: `captured → contacted → replied → booked | no_show | lost`. Email pipeline transitions `captured→contacted→replied` automatically; chatbot/books transition to `booked`.
- **Fallback if Apollo key missing/budgeted:** consume a bundled JSON file `/backend/seed/apollo_sample_leads.json` of ~20 realistic marketing-agency leads (realistic names, titles, emails at example.com, real industries). These must NOT use `example@example.com` boilerplate — use realistic agency domain patterns. Lead rows tagged `source='apollo_sample'`. This keeps the dashboard populated without burning Apollo quota.
  `ASSUMPTION:` owner will provide `APOLLO_API_KEY` if they want the live call. If absent at build time, ship the sample file and document the swap path in §9.
- CRM lead detail page shows the full Apollo enrichment blob cleanly.

## 6. Data model

PostgreSQL schema via SQLAlchemy. (All `created_at`/`updated_at` default `now()`.)

```sql
organizations (id uuid pk, name, external_id, industry, employee_count)
leads (
  id uuid pk default gen_random_uuid(),
  org_id uuid fk,
  first_name, last_name, email unique,
  title, linkedin_url,
  source text,            -- 'apollo' | 'apollo_sample' | 'email_inbound' | 'manual'
  status text,            -- captured|contacted|replied|booked|no_show|lost
  apollo_person_id text,
  enriched_data jsonb,
  last_activity_at timestamptz,
  created_at, updated_at
)
email_threads (
  id uuid pk,
  lead_id uuid fk, gmail_thread_id text unique, subject text, status text
)
email_messages (
  id uuid pk default gen_random_uuid(),
  thread_id uuid fk,
  gmail_message_id text unique,
  direction text,            -- 'inbound' | 'outbound'
  from_email, to_email, subject, body_text,
  intent text,               -- from Groq 8b
  intent_confidence float,
  reply_latency_ms int,      -- outbound: time since inbound arrived
  arrived_at, sent_at, created_at
)
chat_sessions (
  id uuid pk, lead_id uuid fk, state text,        -- GREETING|INTENT_CONFIRM|PROPOSE_TIMES|CONFIRM|BOOK|DONE|LOST
  proposed_slots jsonb, retry_count int default 0,
  created_at, updated_at
)
chat_messages (
  id uuid pk, session_id uuid fk, direction text, text text, created_at
)
meetings (
  id uuid pk, lead_id uuid fk, source text,        -- 'chatbot'|'email'|'manual'
  google_event_id text unique,
  title, start_at timestamptz, end_at timestamptz, hangout_link,
  status text,            -- booked|confirmed|completed|cancelled|no_show
  created_at, updated_at
)
activity_events (
  id bigserial pk, type text,            -- email_inbound|email_outbound|chat_message|meeting_booked|lead_status_change|apollo_sync
  lead_id uuid, payload jsonb, created_at timestamptz default now()
)
kv (key text pk, value text)            -- gmail_last_history_id etc.
demo_metrics_cache (          -- materialized dashboard counters; refresh via endpoint /api/metrics/recompute
  leads_count int, meetings_count int, est_cost_saved numeric, est_hours_saved numeric, avg_reply_latency_ms int, success_rate numeric
)
```

Cost-saved derivation (display only): `est_hours_saved = count(meetings)*0.75 + count(outbound_replies)*0.25` (rule-of-thumb; documented in UI tooltip as "based on $60/hr SDR time × 75%). `est_cost_saved = est_hours_saved * 60`. `ponytail: heuristic cost numbers, demo-only; real ROI model not built here.`

## 7. Dashboard / CRM UI spec

Frontend routes (App Router):
- `/` — Overview
- `/leads` — CRM/leads table
- `/leads/[id]` — lead detail
- `/calendar` — calendar view
- `/activity` — live inbox + chat feed (the money-shot page during the call)
- `/demo/chat` — the prospect chatbot widget (open in second tab during call)
- `/settings/apollo` — sync trigger + status (owner-visible, not demoed unless asked)

Shadcn components to install: `card, table, badge, button, input, tabs, calendar, sonner` (toast), `skeleton`, `avatar`.

### 7.1 Overview `/`
- 4 KPI cards (top): **Leads captured** (count), **Meetings booked** (count, % of leads), **Est. cost / hours saved** (`$X / Yh`), **Avg. reply latency** (`X.Xs`).
- Below: a small `Pipeline by status` horizontal bar (captured/contacted/replied/booked/no-show/lost counts).
- Small `Last 14 days` activity sparkline (activity_events grouped by day).
- All values come from `/api/metrics` (auto-refresh every 5 s during demo so live email arrival bumps numbers visibly).

### 7.2 CRM leads `/leads`
- Table columns: Name | Company | Title | Source (badge: Apollo / Inbound / Sample) | Status (colored badge) | Last activity | Outcome.
- Filters: text search, source filter, status filter.
- Row click → `/leads/[id]` (timeline: enrichment data, email thread, chat transcript, meetings).
- "Sync Apollo" button in toolbar (calls `/api/leads/sync-apollo`, shows toast on completion, refreshes table).

### 7.3 Calendar `/calendar`
- Month view (Shadcn `Calendar` + custom list) showing booked meetings as chips.
- Right rail: upcoming meetings list with time, lead, hangout link, Confirm/Cancel actions (confirm sets `meetings.status='confirmed'`; cancel → `cancelled`, lead back to `contacted` — owner-only for demo drama).

### 7.4 Activity `/activity` (live feed — main demo page)
- Two panes stacked or side-by-side:
  - **Inbox log:** stream of `{time, from, subject, intent badge, reply latency, AI reply excerpt}`. New rows animate in at top.
  - **Chat log:** stream of chatbot turns (lead, direction, text, state badge, booking events inline).
- Real-time via **SSE**: `GET /api/activity/stream` (text/event-stream, one event row per new activity_event since connection). Backend pushes events as they're written.
- A pinned banner at top showing current `avg_reply_latency_ms` so Parth sees the ~4 s number tick live.
- This is the page Tirth shares during the email + chatbot demo moments.

## 8. Seed / demo data plan

Pre-seed via `/backend/seed/run_seed.py` (idempotent, run on `make seed`):
- **24 historical leads** (mix of `apollo` and `apollo_sample`): statuses ~ 8 captured, 6 contacted, 4 replied, 4 booked, 1 no_show, 1 lost. Realistic marketing-agency personas (CMOs, founders, growth leads) at fictional-but-plausible agency domains.
- **30 historical email threads/messages** across those leads over "past 14 days": inbound + outbound pairs, real reply body content (NOT lorem — write 6 distinct reply templates in `seed/reply_templates.py`).
- **8 past meetings** in the calendar over the past 14 days (mix confirmed/completed/cancelled), each linked to a lead.
- **18 past chat-bot sessions** with picks to populate CRM timeline variety.
- **~600 activity_events** across 14 days so the sparkline looks alive.
- **demo_metrics_cache** pre-computed: leads_count=24, meetings_count=8, est_hours_saved=49h, est_cost_saved=$2940, avg_reply_latency_ms=3700, success_rate=0.42.
- **ON THE LIVE CALL** (not seeded — actually happens):
  1. From prospect Gmail → send one email to monitored inbox. Within ~4 s an AI reply lands; activity feed shows it; Overview KPIs tick.
  2. Open `/demo/chat` in a second tab as the prospect. Negotiate 2 turns → bot proposes times → prospect accepts → bot BOOKS → meeting appears in Calendar view + Overview + Activity feed.
- After the call: nothing needs cleanup (demo data stays).

## 9. Env vars / secrets checklist

`/backend/.env` (gitignored, never committed):
```
# Groq
GROQ_API_KEY=             # gsk_...
GROQ_MODEL_TRIAGE=llama-3.1-8b-instant
GROQ_MODEL_DRAFT=llama-3.3-70b-versatile
GROQ_MODEL_DRAFT_FAST_FALLBACK=false   # set true if dry-run misses 4s budget

# Google OAuth (monitored inbox only)
GCP_CLIENT_ID=
GCP_CLIENT_SECRET=
GMAIL_REFRESH_TOKEN=      # obtained via first-run /auth/start + /auth/callback
GMAIL_MONITORED_EMAIL=    # e.g. asdr.demo@gmail.com
GMAIL_PROSPECT_EMAIL=     # throwaway account used as prospect
GMAIL_POLL_INTERVAL_MS=1500

# Google Calendar
GOOGLE_CALENDAR_ID=primary

# Apollo
APOLLO_API_KEY=           # blank → use bundled sample JSON
APOLLO_SAVED_QUERY_JSON={"person_titles":["Founder"],"organization_num_employees_ranges":["1-10"],"q_organization_keyword":"social media marketing agency"}

# Postgres
DATABASE_URL=postgresql+psycopg://asdr:asdr@localhost:5432/asdr_demo

# Set this once (the seeded demo lead used by /demo/chat)
DEMO_LEAD_ID=

# Misc
CORS_ORIGINS=http://localhost:3000
CHAT_WORKING_HOURS=09:00-18:00
CHAT_TZ=Asia/Kolkata
```
`/frontend/.env.local`:
```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```
None of these have real values. Owner fills before call. DeepSeek must NOT invent real secrets.

## 10. Step-by-step build checklist for DeepSeek

> Execute in order. Tick each. Do not parallelize unless two steps say "independent — parallelize."

**A. Scaffold**
1. `git init`-ready repo (already a repo). Create `/backend`, `/frontend`, `/docs`, `.gitignore` (node_modules, .env, .venv, __pycache__, .next, build).
2. Scaffold backend: `python -m venv .venv`, `pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg psycopg pydantic-settings google-auth google-auth-oauthlib google-api-python-client httpx chromadb groq python-dotenv`. Pin in `backend/requirements.txt`.
3. Scaffold frontend: `npx create-next-app@latest frontend --typescript --tailwind --app --eslint` (Next 16). `cd frontend && npx shadcn@latest init && npx shadcn@latest add card table badge button input tabs calendar sonner skeleton avatar`.
4. `Makefile` with targets: `backend-dev` (uvicorn), `frontend-dev` (next dev), `seed` (python seed/run_seed.py), `poller` (run module that starts Gmail poller), `auth-start` (open `/auth/start` URL).

**B. DB + models**
5. SQLAlchemy models matching §6 (one `models.py`).
6. Alembic? NO — demo corners cut. `backend/db/init_db.py` does `Base.metadata.create_all`. Run on `make seed`.
7. Insert dummy organization for demo leads' companies.
8. Pydantic schemas for all endpoints (`schemas.py`).

**C. Gmail OAuth + poller**
9. OAuth client wiring: `backend/gmail/oauth.py` (`get_credentials`, refresh flow using stored refresh token).
10. `backend/gmail/poller.py` — asyncio loop per §2 exact algorithm.
11. `backend/gmail/classify.py` — Groq 8b call returning structured intent JSON.
12. `backend/gmail/draft.py` — Groq 70b reply draft, with the inbound email + thread context (last 2 messages from Chroma for that lead if exists).
13. `backend/gmail/send.py` — `messages.send` with In-Reply-To + References.
14. `backend/api/router.py` endpoints: `GET /auth/start`, `GET /auth/callback`, `GET /health`.

**D. Calendar**
15. `backend/calendar/client.py` — `events.insert` + `events.list(primary, timeMin=now-7d, timeMax=now+30d)`.
16. `backend/api/meetings.py`: `POST /api/meetings/book`, `GET /api/meetings`, `POST /api/meetings/:id/confirm`, `POST /api/meetings/:id/cancel`.
17. On book success: insert meetings row, update lead status, write activity_event `{type:'meeting_booked'}`.

**E. Chatbot**
18. `backend/chat/session.py` — state machine impl + persistence (chat_sessions, chat_messages).
19. `backend/chat/slots.py` — generate 3 slots within CHAT_WORKING_HOURS avoiding booked meetings.
20. `backend/chat/llm_turn.py` — Groq 70b turn (input: state, history, user text → classify accept/propose_alt/decline/question + draft reply).
21. `backend/api/chat.py`: `POST /api/chat/message`, returns per §3.

**F. Apollo**
22. `backend/apollo/client.py` — People Search call; fall back to `seed/apollo_sample_leads.json` if no key.
23. `backend/api/leads.py`: `POST /api/leads/sync-apollo`, `GET /api/leads`, `GET /api/leads/:id`, `GET /api/leads/:id/timeline`.
24. Map Apollo people → leads rows + lead.created → status pipeline per §5.

**G. Activity feed + metrics**
25. `backend/api/activity.py`: `GET /api/activity` (paginated), `GET /api/activity/stream` (SSE).
26. `backend/api/metrics.py`: `GET /api/metrics` (read cache), `POST /api/metrics/recompute`.
27. Central event emitter (`backend/events.py`): every write site calls `emit(event)` → inserts activity_event + writes to in-memory async queue → SSE consumers drain. `ponytail: in-process asyncio.Queue, fine for one laptop; not durable, on crash the SSE stream dies and client reconnects.`

**H. Frontend pages**
28. Layout: top nav (`/`, `/leads`, `/calendar`, `/activity`, `/demo/chat`), Shadcn `sonner` Toaster, `/api` client wrapping fetch with `NEXT_PUBLIC_API_BASE`.
29. `/` Overview (§7.1) — 4 KPI cards + pipeline bars + sparkline; refresh 5 s.
30. `/leads` (§7.2) + `/leads/[id]` (timeline).
31. `/calendar` (§7.3).
32. `/activity` (§7.4) — EventSource SSE, two panes, latency banner.
33. `/demo/chat` — chat input + message list; POST to `/api/chat/message`; show state badge; on `booked_meeting` show meet link inline + toast + push to activity feed automatically via SSE.
34. `/settings/apollo` — sync trigger (not demoed unless asked).

**I. Seed**
35. `backend/seed/run_seed.py` per §8 (idempotent: wipe + recreate in dev only — guard with `ENV=dev` check).
36. `backend/seed/apollo_sample_leads.json` ~20 leads.
37. `backend/seed/reply_templates.py` 6 templates (no lorem).
38. `make seed` runs init_db + seed.

**J. Boot self-check**
39. `backend/selfcheck.py` — `__main__` asserts: env present (skip gracefully telling which key missing), DB reachable, Groq reachable (lists one model), Gmail OAuth access token refreshes, Calendar returns events.list, ChromaDB client OK. Exits 0 on success, NonZero listing failures.

**K. README**
40. `README.md` — minimal: env checklist (§9), start order (`make seed` → `make auth-start` once → `make backend-dev` + `make poller` + `make frontend-dev`), dry-run (§11).

## 11. Pre-call validation checklist

Run **T −15 min** to call. Tick each. If any fails, fix or escalate; do NOT improvise live.

**T-120 min — Foundations**
1. `python backend/selfcheck.py` → all green.
2. `make seed` → confirms seed inserted numbered rows.
3. Start Postgres locally, confirm `psql` connects to `asdr_demo`.
4. `cd frontend && npm run build` passes typecheck/lint.

**T-60 min — OAuth + first reply**
5. Open `http://localhost:8000/auth/start` in monitored Gmail → consent → callback writes refresh token to `.env` (or `secrets.json`).
6. From prospect Gmail (`GMAIL_PROSPECT_EMAIL`) send test email "Interested in ASDR demo" → monitored inbox.
7. Watch `make poller` logs: should detect within 1.5–3 s, classify, draft, send.
8. Check prospect Gmail received AI reply. Measure end-to-end time (from send-button click to inbox arrival) — must be **< 4 s**.
9. If > 4 s: set `GROQ_MODEL_DRAFT_FAST_FALLBACK=true`, restart backend, retest. If still > 4 s: drop triage to 8b-only (no separate triage call), retest.
10. Open `/activity` in browser — should show inbound + outbound rows with latency badge.

**T-30 min — Chatbot + calendar**
11. Open `/demo/chat` in incognito tab → reply "I want a demo."
12. Bot → confirms intent → proposes 3 times.
13. Reply "any of those is too early, can we do afternoon?" → bot proposes afternoon slots.
14. Reply "perfect, the 3 PM one" → bot confirms → books.
15. Confirm Google Calendar now has the event (check Gmail calendar app on phone or `/calendar` page).
16. Confirm `/calendar` page shows new meeting within 3 s.
17. Confirm `/activity` page shows `meeting_booked` event appeared live.
18. Confirm `/` overview KPIs ticked (meetings booked +1, hours/cost saved +n).

**T-20 min — Apollo**
19. Click "Sync Apollo" on `/leads`. Either live Apollo call pulls N leads, or sample file inserts N rows (verify `source` badge).
20. Open a lead detail page — enrichment data present, no placeholder text.

**T-10 min — Final sweep**
21. Reload every page; confirm no errors in console, no skeletons stuck.
22. Confirm no `lorem`, `TODO`, `placeholder`, `test@test.com` anywhere in visible UI (grep `frontend/` for these).
23. Set laptop "do not sleep," close other apps eating CPU, confirm Chrome stable.
24. Have prospect Gmail logged in in a second window so the live send + received reply are visible side-by-side on screen during the call.

**During call — the 15 min**
- Minute 0–3: Overview pitch + KPIs.
- Minute 3–6: Send live email from prospect Gmail → 4 s reply appears in `/activity`.
- Minute 6–10: Live chatbot negotiation → book → calendar updates live.
- Minute 10–12: Show CRM `/leads` with Apollo enrichment.
- Minute 12–14: Show past meetings / pipeline / cost-saved cards.
- Minute 14–15: Q&A, replay of activity feed if asked.

---

**End of plan.** DeepSeek: do not add features beyond this file. If a step is impossible (e.g., Apollo endpoint path changed, Groq model removed), stop, log the blocker, ask Tirth — do not substitute silently.