# ASDR Backend

FastAPI backend for the Autonomous SDR & Ops Router MVP: inbound email webhook → Groq triage → ChromaDB RAG → Groq draft → Postgres, with a Kanban-ready REST API and a public demo endpoint.

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then fill in GROQ_API_KEY and Gmail OAuth vars
```

## Gmail setup
1. Go to [Google Cloud Console](https://console.cloud.google.com), create a project, enable **Gmail API**
2. Create an OAuth 2.0 Client ID (Desktop app type)
3. Set `GMAIL_CLIENT_ID` and `GMAIL_CLIENT_SECRET` in `.env`
4. Run once: `python scripts/gmail_auth.py` — opens a browser for OAuth consent
5. Copy the printed refresh token to `GMAIL_REFRESH_TOKEN` in `.env`
6. Set `GMAIL_USER_EMAIL=your.email@gmail.com` in `.env`

## Env vars

| Var | Default | Notes |
|---|---|---|
| `GROQ_API_KEY` | — | **Required**. Missing/placeholder → agents raise, webhook/demo return 502 |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | |
| `DATABASE_URL` | `postgresql+psycopg://asdr:asdr@localhost:5432/asdr` | docker-compose overrides host to `db` |
| `CLIENT_COMPANY_NAME` | `Apex Digital` | Used in agent prompts |
| `CHROMA_PATH` | `./chroma_data` | Vector store dir, seeded on startup from `KB_SEED_FILE` if empty |
| `KB_SEED_FILE` | `./mock_kb.txt` | |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated |
| `GMAIL_CLIENT_ID` | — | Google Cloud OAuth client ID |
| `GMAIL_CLIENT_SECRET` | — | Google Cloud OAuth client secret |
| `GMAIL_REFRESH_TOKEN` | — | Run `python scripts/gmail_auth.py` once to get this |
| `GMAIL_USER_EMAIL` | — | Email address to monitor and send from |
| `MAIL_MODE` | `hitl` | `auto` = send immediately, `hitl` = draft pending |
| `MAIL_POLL_INTERVAL` | `30` | Seconds between inbox checks |
| `CHATBOT_URL` | `http://localhost:3000/chat` | URL mail bot directs leads to |

## Run

```powershell
uvicorn main:app --reload --port 8000
```

Send a mock inbound email:

```powershell
python scripts/send_mock_email.py sales
python scripts/send_mock_email.py spam
```

## Endpoints (curl)

```bash
# Health
curl http://localhost:8000/health

# Webhook: ingest email, run triage → RAG → draft, persist (201)
curl -X POST http://localhost:8000/api/v1/webhooks/email \
  -H "Content-Type: application/json" \
  -d '{"sender":"jane@acme.com","subject":"Pricing question","body":"Hi, what does a website redesign cost?"}'

# List emails (newest first), optional status filter
curl "http://localhost:8000/api/v1/emails"
curl "http://localhost:8000/api/v1/emails?status=pending"

# Get one (404 → {"error":{"code":"NOT_FOUND",...}})
curl http://localhost:8000/api/v1/emails/<uuid>

# Edit draft and/or status (status ∈ pending|approved|discarded)
curl -X PATCH http://localhost:8000/api/v1/emails/<uuid> \
  -H "Content-Type: application/json" \
  -d '{"ai_draft":"edited text","status":"approved"}'

# Public demo: scrape URL for context, draft reply (never persists; 502 SCRAPE_FAILED)
curl -X POST http://localhost:8000/api/v1/demo/run \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","sender_name":"John","email_body":"Do you offer SEO services?"}'

# Settings: get current mail mode
curl http://localhost:8000/api/v1/settings

# Settings: toggle auto / hitl
curl -X PATCH http://localhost:8000/api/v1/settings \
  -H "Content-Type: application/json" \
  -d '{"mail_mode":"auto"}'
```

Error shape (all endpoints): `{"error": {"code": "STRING", "message": "..."}}`
