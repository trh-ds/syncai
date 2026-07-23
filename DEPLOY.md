# Deploy

Frontend → Vercel. Backend → Render (per TECH_STACK.md).

## Backend (Render)

1. Render dashboard → **New → Blueprint** → select this repo. `render.yaml` creates:
   - `asdr-backend` web service (Docker, from `backend/Dockerfile`)
   - `asdr-db` managed Postgres (free plan), `DATABASE_URL` auto-wired
   - 1 GB persistent disk at `/data/chroma` for ChromaDB
2. Set these env vars manually in the Render dashboard (`sync: false` ones):
   - `GROQ_API_KEY` — your `gsk_...` key
   - `CORS_ORIGINS` — your Vercel URL, e.g. `https://your-app.vercel.app`

## Frontend (Vercel)

1. Vercel → **Add New → Project** → import repo, set **Root Directory** to `frontend`.
2. Env var: `NEXT_PUBLIC_API_URL` = your Render backend URL, e.g. `https://asdr-backend.onrender.com`.
3. Deploy.

## Caveat: NEXT_PUBLIC_API_URL is build-time inlined

Next.js inlines `NEXT_PUBLIC_*` vars into the JS bundle **at build time**.
Changing the backend URL later requires a **rebuild/redeploy** of the frontend
(Vercel: Redeploy; Docker: `docker compose build frontend`). Setting it at
runtime has no effect. Same applies to the compose build arg.

## Env var summary

| Var | Where |
|---|---|
| `GROQ_API_KEY`, `GROQ_MODEL`, `CLIENT_COMPANY_NAME` | Render dashboard |
| `DATABASE_URL` | Auto from Render Postgres |
| `CHROMA_PATH`, `KB_SEED_FILE` | Set in render.yaml, no action |
| `CORS_ORIGINS` | Render dashboard (= Vercel URL) |
| `NEXT_PUBLIC_API_URL` | Vercel project env (= Render URL) |
