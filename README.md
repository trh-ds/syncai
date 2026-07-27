# ASDR Demo — AI Sales Development Rep

Localhost demo of an AI-powered SDR that handles email outreach, lead qualification, chatbot negotiation, and meeting booking.

## Stack

- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, Tailwind v4, Shadcn UI
- **Backend:** FastAPI, Python 3.12+, Uvicorn
- **LLM:** Groq (`llama-3.1-8b-instant` + `llama-3.3-70b-versatile`)
- **RAG:** ChromaDB (embedded)
- **DB:** PostgreSQL 16 + SQLAlchemy 2.0 (async)
- **Mail/Calendar:** Gmail API + Google Calendar API
- **Leads:** Apollo People Search API

## Prerequisites

- Python 3.12+
- Node.js 22+
- PostgreSQL 16 running locally
- Groq API key (`gsk_...`)
- Google Cloud project with OAuth 2.0 client (Gmail + Calendar scopes)
- Apollo API key (optional — uses bundled sample data if absent)

## Setup

### 1. Environment

```bash
cp backend/.env.example backend/.env   # fill in secrets
cp frontend/.env.local.example frontend/.env.local  # NEXT_PUBLIC_API_BASE=http://localhost:8000
```

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### 3. Frontend

```bash
cd frontend
npm install
```

### 4. Database

Ensure PostgreSQL is running with a database `asdr_demo` and user `asdr`:

```sql
CREATE USER asdr WITH PASSWORD 'asdr';
CREATE DATABASE asdr_demo OWNER asdr;
```

### 5. Google OAuth (first run only)

```bash
make auth-start   # opens http://localhost:8000/auth/start
```

Complete the OAuth consent screen. The callback saves the refresh token to `.env`.

## Run

```bash
# Terminal 1 — Database seed (once)
make seed              # ENV=dev required

# Terminal 2 — Backend
make backend-dev       # http://localhost:8000

# Terminal 3 — Gmail poller
make poller

# Terminal 4 — Frontend
make frontend-dev      # http://localhost:3000
```

## Env vars checklist

See `DEMO_PLAN.md` §9 for the complete `.env` template.

## Pre-call dry-run

See `DEMO_PLAN.md` §11 for the full validation checklist.
