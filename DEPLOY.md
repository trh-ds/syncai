# Deploy

Frontend → Vercel. Backend → Render. Database + Auth → Supabase.

> **Why Supabase for the DB:** Render's free Postgres auto-expires after ~30–90
> days and the data is gone. Supabase's free tier (500 MB DB, 50k MAU, 2 projects)
> is permanent. It also bundles Auth (email/password + Google OAuth) at $0.

## 0. Supabase (do this first)

1. supabase.com → **New project** (free). Note the DB password.
2. **Settings → Database** → copy the connection string → this is your `DATABASE_URL`
   (prefix it `postgresql+psycopg://` for SQLAlchemy).
3. **Settings → API** → copy `SUPABASE_URL`, `anon` key, and **JWT secret** (Settings → JWT).
4. Auth: **Authentication → Providers** → enable Email and Google. For Google, add
   your Google OAuth client; set redirect URLs to your Vercel domain.
5. Free projects auto-pause after 7 days idle — the repo includes
   `.github/workflows/keepalive.yml` (every 3 days). Set repo variable
   `HEALTH_URL` = `https://your-backend.onrender.com/health`.

## 1. Backend (Render)

1. Render dashboard → **New → Blueprint** → select this repo. `render.yaml` creates:
   - `asdr-backend` web service (Docker, from `backend/Dockerfile`)
   - 1 GB persistent disk at `/data/chroma` for ChromaDB
2. Set env vars in the Render dashboard (`sync: false` ones):
   - `GROQ_API_KEY` — your `gsk_...` key
   - `DATABASE_URL` — Supabase connection string from step 0
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`
   - `CORS_ORIGINS` — your Vercel URL
   - `PUBLIC_API_URL` — your Render URL (used in unsubscribe links)
   - `WEB_URL` — your Vercel URL (OAuth/billing redirects)
    - Optional: `SLACK_WEBHOOK_URL`, `APOLLO_API_KEY`
3. Note: free web services sleep after 15 min idle (~30–60s cold start). The
   keep-alive workflow doubles as a warmer.

## 2. Frontend (Vercel)

1. Vercel → **Add New → Project** → import repo, set **Root Directory** to `frontend`.
2. Env vars:
   - `NEXT_PUBLIC_API_URL` = your Render backend URL
   - `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` = from step 0
3. Deploy.

## Caveat: NEXT_PUBLIC_* is build-time inlined

Next.js inlines `NEXT_PUBLIC_*` vars into the JS bundle **at build time**.
Changing them later requires a **rebuild/redeploy** of the frontend.

## Env var summary

| Var | Where |
|---|---|
| `GROQ_API_KEY`, `GROQ_MODEL`, `CLIENT_COMPANY_NAME` | Render dashboard |
| `DATABASE_URL` | Supabase connection string (set in Render) |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET` | Render dashboard |
| `SLACK_WEBHOOK_URL`, `APOLLO_API_KEY` | Render dashboard (optional) |
| `BUSINESS_NAME`, `BUSINESS_ADDRESS` | render.yaml defaults (CAN-SPAM footer) |
| `PUBLIC_API_URL`, `WEB_URL`, `CORS_ORIGINS` | Render dashboard |
| `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_*` | Vercel project env |
| `CHROMA_PATH`, `KB_SEED_FILE` | Set in render.yaml, no action |
