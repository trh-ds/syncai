# ASDR Frontend

Next.js (App Router) + TypeScript + Tailwind + Shadcn UI dashboard for the
Autonomous SDR & Ops Router MVP. Consumes the FastAPI backend per
`../API_CONTRACTS.md`.

## Setup

```powershell
npm install
Copy-Item .env.example .env.local   # set NEXT_PUBLIC_API_URL if not localhost:8000
```

## Run

```powershell
npm run dev     # http://localhost:3000
npm run build   # production build
npm start
```

## Env

| Var | Example | Notes |
|---|---|---|
| NEXT_PUBLIC_API_URL | http://localhost:8000 | Backend base URL. Only env var. Never commit `.env.local`. |

## Pages

- `/` — landing, links to both apps
- `/dashboard` — inbox board (pending / approved / discarded tabs), edit AI
  drafts inline, Approve & Send / Discard via `PATCH /api/v1/emails/{id}`
- `/demo` — public demo: company URL + sample email → `POST /api/v1/demo/run`,
  shows drafted reply and context used. Nothing persisted.
