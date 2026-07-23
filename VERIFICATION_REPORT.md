# ASDR MVP — Wave 3 Verification Report

Date: 2026-07-21 · Verifier: independent test harness (`verify/verify_wave3.py`, `verify/app_shim.py`) + static contract cross-check + `npm run build`.

Method: backend booted with `DATABASE_URL=sqlite+pysqlite:///...` (no Postgres available), placeholder and invalid `GROQ_API_KEY` variants. 26/28 runnable checks passed; frontend production build passed. Static cross-check of every endpoint/field in `API_CONTRACTS.md` against `backend/` and `frontend/lib/api.ts` found no field-name, path, method, or nullability mismatches — all failures below are runtime/logic, not shape.

---

## Findings

### 1. SEVERITY: CRITICAL
- COMPONENT: backend (and contract)
- DESCRIPTION: **App does not boot with stock config.** `agents/rag_agent.py` sets `COLLECTION = "kb"`; Chroma requires collection names of 3+ characters. Lifespan `seed_if_empty()` raises `chromadb.errors.InvalidArgumentError` → uvicorn: `Application startup failed. Exiting.` Proven by booting unmodified `main:app`: process dies before serving `/health`. `DATA_MODELS.md` also mandates collection name `kb`, so the contract itself specifies an invalid name.
- FIX: Rename the collection (e.g. `"kb_store"`) in `rag_agent.py` AND update `DATA_MODELS.md` to match. One-line change each side.

### 2. SEVERITY: WARNING
- COMPONENT: backend
- DESCRIPTION: **LLM failure with a real-but-rejected Groq key returns 500, not 502.** Webhook catches only `RuntimeError`; the Groq SDK raises `groq.AuthenticationError` (not a `RuntimeError` subclass) → falls into the catch-all → `500 {"error":{"code":"INTERNAL_ERROR",...}}`. Observed live: `HTTP 500 ... Invalid API Key`. README promises 502 for agent failures; clients cannot distinguish LLM outage from a server bug. Same gap in `POST /demo/run` LLM path. (Placeholder/missing key correctly returns 502 LLM_ERROR — only SDK-raised errors leak.) Contract error shape still holds, hence WARNING not CRITICAL.
- FIX: In `webhooks.py`/`endpoints.py`, catch `groq.APIError` (or `Exception` from the agent calls) in addition to `RuntimeError`, mapping to 502 `LLM_ERROR`.

### 3. SEVERITY: WARNING
- COMPONENT: backend
- DESCRIPTION: **Status transition rules not enforced.** `DATA_MODELS.md`: "pending → approved | discarded". Observed: `PATCH {"status":"pending"}` on an already-`approved` email returns HTTP 200 and reopens it. Any transition between any states is accepted.
- FIX: In `patch_email`, reject transitions where `record.status != "pending"` (or where target is not reachable from current) with 422/409 error shape.

### 4. SEVERITY: INFO
- COMPONENT: backend
- DESCRIPTION: `agents/groq_client.py` is dead code (nothing imports it) and is broken: `from core.config import get_settings` — `get_settings` does not exist in `core/config.py`. Importing it would raise ImportError.
- FIX: Delete the file (agents use `Groq` directly) or fix the import.

### 5. SEVERITY: INFO
- COMPONENT: frontend
- DESCRIPTION: `EmailCard.tsx` renders action buttons only when `email.ai_draft !== null`, so Spam/Other emails (null draft per contract) can never be approved/discarded from the dashboard — they are stuck in the pending tab.
- FIX: Render the Discard (and optionally Approve) button regardless of `ai_draft` nullability.

### 6. SEVERITY: INFO
- COMPONENT: frontend
- DESCRIPTION: `getEmail()` in `lib/api.ts` is exported but never called (dashboard fetches the list only). Harmless.
- FIX: None required for MVP.

---

## Verified OK (runnable evidence)

- `GET /health` → 200 `{"status":"ok"}`
- `GET /api/v1/emails` → 200 array, keys exactly match contract, newest-first, ISO-8601 `Z` timestamps, spam row `ai_draft: null`
- `?status=pending` filter works; `?status=bogus` → 422 contract error shape
- `GET /emails/{id}` 200; unknown UUID → 404 `NOT_FOUND`; malformed id → 422 shape
- `PATCH` happy path 200 returns full updated object; empty body, invalid status enum, wrong types, malformed JSON → all 422 contract shape; unknown id → 404 `NOT_FOUND`
- Webhook with placeholder key → 502 `{"error":{"code":"LLM_ERROR",...}}`; malformed JSON / missing fields / wrong types → 422 shape
- `POST /demo/run` unreachable URL → 502 `SCRAPE_FAILED` (contract shape); missing fields / malformed JSON → 422 shape
- CORS: preflight allows `http://localhost:3000` (per ENV.md), reflects no other origin
- Frontend `Email` type matches backend `EmailOut` field-for-field (verified against live responses); `api.ts` paths/methods/PATCH payloads/error-shape parsing all match contract; dashboard/demo pages use correct status values and handle `null ai_draft` without crashing
- `npm run build` passes (Next.js 16.2.10, Turbopack, TS strict, all 4 routes static)

## UNVERIFIED (needs real Groq key / real Postgres)

1. Webhook 201 happy path: triage → RAG → draft → persist with a live LLM (incl. `sender_name` extraction, Spam/Other → `ai_draft: null` behavior from real triage).
2. Triage JSON robustness against real model output (`TriageResult` parse failures → 502 path).
3. `POST /demo/run` 200 happy path with a reachable URL + live LLM.
4. RAG retrieval quality/relevance from seeded Chroma KB (seeding itself verified under a shimmed collection name).
5. Postgres-specific behavior: `psycopg` driver, `server_default=func.now()`, index creation — tested on sqlite only.
6. Chroma persistence across restarts (`CHROMA_PATH` reuse).

## Verdict: **NO-GO** for Wave 4 (DevOps)

Finding #1 means the container cannot start — a Docker build would ship a service that crashes on boot. Fixes #1–#3 are small (a few lines total); re-run `verify/verify_wave3.py` after the collection rename (drop `app_shim.py` — it should then pass unmodified) and this becomes GO.


---
## Resolution (orchestrator)
All findings fixed and harness re-run: 28/28 PASS, frontend build green.
1. CRITICAL collection name -> 'knowledge_base' (rag_agent.py + DATA_MODELS.md)
2. WARNING Groq APIError now caught -> 502 LLM_ERROR (webhooks.py, endpoints.py)
3. WARNING PATCH status transitions enforced pending-only -> 422 INVALID_TRANSITION
4. INFO dead agents/groq_client.py deleted
5. INFO null-draft pending cards now show Discard (EmailCard.tsx)
UNVERIFIED items remain pending a real GROQ_API_KEY + Postgres. Verdict: GO for Wave 4.
