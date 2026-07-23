# Project: ASDR — Autonomous SDR & Ops Router (MVP)

## Overview
B2B SaaS MVP: inbound email → Groq LLM triage → ChromaDB RAG → AI draft reply → Postgres → Next.js Kanban dashboard for approve/edit/discard, plus a public `/demo` page for live pitches. Single-tenant, no auth. See PLAN.md for full blueprint.

## Wave 1 — Architecture (BLOCKING)
- [x] API_CONTRACTS.md
- [x] DATA_MODELS.md
- [x] TECH_STACK.md
- [x] ENV.md

## Wave 2 — Parallel Build
| Sub-Agent | Assignment | Status |
|-----------|-----------|--------|
| backend-dev | FastAPI, webhook, triage/rag/draft agents, ChromaDB, SQLAlchemy+Postgres, mock sender script | DONE |
| frontend-dev | Next.js scaffold, /dashboard Kanban + EmailCard, /demo page, API client | DONE |

## Wave 3 — Verification
- [x] Test every endpoint against API_CONTRACTS.md (28/28, verify/verify_wave3.py)
- [x] VERIFICATION_REPORT.md, fix CRITICALs (all 5 findings fixed, harness re-run green)
- [ ] End-to-end with real Groq key + Postgres (needs GROQ_API_KEY in backend/.env)

## Wave 4 — DevOps
- [x] Dockerfiles (frontend, backend)
- [x] docker-compose.yml (frontend + backend + Postgres) — `docker compose config` validated; image builds pending Docker Desktop running
- [x] GitHub Actions (backend import check, frontend lint+build, docker build smoke)
- [x] Deploy config: render.yaml + DEPLOY.md (Vercel frontend, Render backend)

## Known Unknowns
None — all stack decisions locked (see TECH_STACK.md).

## Out of Scope (Phase 5, post-sale)
Gmail API ingestion, Slack webhooks, HubSpot CRM, auth/multi-tenancy, real email sending ("Approve & Send" only flips status).
