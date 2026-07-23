# Tech Stack (locked)

| Layer | Choice | Rationale |
|---|---|---|
| Frontend | Next.js (App Router), React, TypeScript, Tailwind, Shadcn UI | Per PLAN.md |
| Backend | Python 3.12, FastAPI, Uvicorn | Per PLAN.md |
| LLM | Groq, model `llama-3.3-70b-versatile` (env `GROQ_MODEL`), raw `groq` SDK | 3 prompt calls don't justify LangChain |
| JSON validation | Pydantic | Strict triage output parsing |
| Vector DB | ChromaDB, in-process, persisted to `./chroma_data` | No external account; one mock KB |
| RDBMS | PostgreSQL 16 (docker-compose service) | Per PLAN.md |
| ORM | SQLAlchemy 2.x + psycopg[binary] | ORM + DB are a pair, not alternatives |
| Demo scrape | BeautifulSoup4 + httpx | Simple text grab for /demo |
| Auth | None (single-tenant demo) | Phase 5 adds real auth |
| Containerization | Docker + docker-compose | Per PLAN.md |
| CI/CD | GitHub Actions: lint + test + build | Per PLAN.md |
| Hosting | Vercel (frontend), Render (backend) | ECS overkill for MVP |
| Email send | Mocked — "Approve & Send" only sets status | Per PLAN.md |

## Pipeline (per inbound webhook)
1. Validate payload (Pydantic).
2. Triage: Groq call with strict-JSON system prompt → `{intent, sender_name, summary}`.
3. If intent ∈ {Sales, Support}: query ChromaDB top-k=3 for context.
4. Draft: Groq call with email + triage JSON + context → reply text.
5. Insert into `emails` with status `pending`. Return record.
