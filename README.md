# ASDR

Autonomous SDR & Ops Router: inbound email webhook → Groq triage → ChromaDB
RAG → Groq-drafted reply → Postgres, with a Kanban dashboard and public demo.

## Quickstart

```bash
cp .env.example .env   # fill in GROQ_API_KEY
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000 (health: `/health`)

## Docs

- [backend/README.md](backend/README.md) — API endpoints, backend setup
- [frontend/README.md](frontend/README.md) — pages, frontend setup
- [DEPLOY.md](DEPLOY.md) — Vercel + Render deployment
- [ENV.md](ENV.md) — environment variables
