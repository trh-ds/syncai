# SyncAI (ASDR) — End-to-End Cost Model

All prices below are pulled from vendor pricing pages in **July 2026**. Token counts are measured
from the actual prompts in this repo, not guessed. Sources at the bottom.

---

## 1. What actually costs money

| Component | In the code | Real cost |
|---|---|---|
| Groq LLM (triage) | `gmail/classify.py` → `llama-3.1-8b-instant` | metered per token |
| Groq LLM (drafting + chat) | `gmail/draft.py`, `chat/llm_turn.py` → `llama-3.3-70b-versatile` | metered per token |
| Gmail API (read + send) | `gmail/poller.py`, `gmail/send.py` | **$0** (quota-limited, not billed) |
| Google Calendar API | `api/meetings.py` → `gcal.client` | **$0** — *module does not exist, see §7* |
| Apollo lead sourcing | `apollo/client.py` | **$0** — *reads a local JSON file, never calls Apollo* |
| ChromaDB / RAG | only in `selfcheck.py` | **$0** — *not implemented; dead dependency, see §7* |
| PostgreSQL 16 | `docker-compose.yml` | hosting |
| FastAPI backend + Next.js frontend | 2 containers | hosting |
| Sending mailbox | `GMAIL_MONITORED_EMAIL` | Google Workspace seat |

Everything else in the product (dashboard, leads table, activity feed, SSE stream, metrics,
slot generation in `chat/slots.py`) is pure Postgres + CPU — it costs hosting, nothing more.

---

## 2. Groq unit economics (measured)

Groq list prices:

| Model | Input | Output |
|---|---|---|
| `llama-3.1-8b-instant` | $0.05 / 1M tok | $0.08 / 1M tok |
| `llama-3.3-70b-versatile` | $0.59 / 1M tok | $0.79 / 1M tok |

Measured system-prompt sizes in this repo: classify 181 tok, draft 222 tok, chat 242 tok.

### Per-operation cost

| Operation | Model | Input tok | Output tok | Cost / call |
|---|---|---|---|---|
| Email triage (`classify_message`) | 8B | ~360 | ~40 | **$0.0000212** |
| Reply draft (`draft_reply`, capped 150 words) | 70B | ~460 | ~200 | **$0.000429** |
| Chat turn (`process_turn`, 10-msg history, 100-word cap) | 70B | ~670 | ~140 | **$0.000506** |

Derived:

- **One inbound email fully handled** (triage + draft + send) = **$0.00045** → **$0.45 per 1,000 emails**
- **One chat conversation** (8 turns avg) = **$0.0040** → **$4.05 per 1,000 conversations**

### The 11× lever

Setting `GROQ_MODEL_DRAFT_FAST_FALLBACK=true` routes drafting and chat to the 8B model:

| Operation | 70B | 8B fallback | Saving |
|---|---|---|---|
| Reply draft | $0.000429 | $0.000039 | 11.0× |
| Chat turn | $0.000506 | $0.0000447 | 11.3× |

At any volume below ~50k operations/month this is a rounding error. Above that it is the single
biggest cost dial in the product.

---

## 3. Hosting — three real deployment shapes

The stack is 4 containers: postgres, seed (one-shot), backend, frontend.

**A. Single VPS, docker compose (cheapest, what the repo is built for)**

| Item | Price |
|---|---|
| Hetzner CX23 — 2 vCPU / 4 GB / 40 GB NVMe | €3.99/mo |
| IPv4 address | €0.50/mo |
| **Total** | **€4.49/mo ≈ $5.20/mo** |

Fits all four containers. No managed backups — add your own `pg_dump` cron or a €1/mo snapshot.

**B. Render (managed, no ops)**

| Item | Price |
|---|---|
| Frontend web service — Starter (512 MB) | $7/mo |
| Backend web service — Standard (2 GB, needed today, see §7) | $25/mo |
| Postgres Basic-256mb | $6/mo |
| **Total** | **$38/mo** |

**C. Vercel frontend + Render backend**

| Item | Price |
|---|---|
| Vercel Pro (1 seat, 1 TB bandwidth incl.) | $20/mo |
| Render backend Standard | $25/mo |
| Render Postgres Basic-256mb | $6/mo |
| **Total** | **$51/mo** |

Plus, on all three: **domain ~$12/yr ≈ $1/mo**. TLS is free everywhere.

---

## 4. Google costs

- **Gmail API: free.** 80,000,000 quota units/day per project; 6,000 units/min per user.
  The poller runs `history.list` (2 units) every 5 s = **24 units/min**. A sent reply is 100 units,
  a message fetch 20. You cannot realistically hit the quota with this product.
- **Google Calendar API: free.**
- **The mailbox is not free.** Google Workspace (India pricing, July 2026):

| Plan | Price/user/mo | Note |
|---|---|---|
| Base | ₹99 (₹49.50 promo to Nov 10, 2026) | max 20 users, 20 GB pooled |
| Business Starter | ₹270 (~$3.20) | 30 GB/user |
| Business Standard | ₹1,080 (~$12.90) | 2 TB/user |

**Business Starter is enough** — the product only needs Gmail send/read + Calendar.

---

## 5. Apollo (only if the client wants real lead sourcing)

`apollo/client.py` reads `seed/apollo_sample_leads.json`. **Today this costs $0** and returns the
same 20-odd bundled leads. Real Apollo lead sourcing is a per-seat subscription:

| Plan | Annual billing | Monthly billing |
|---|---|---|
| Free | $0 | — |
| Basic | $49/user/mo | $59 |
| Professional | $79/user/mo | $99 |
| Organization | $119/user/mo (3-seat min) | $149 |

This is the **largest single line item** in any real deployment — bigger than hosting and LLM combined
at typical volumes. Quote it separately and make the client aware it is their subscription, not yours.

---

## 6. Hard ceilings that change the price when crossed

These are volume walls, not cost curves. Know them before quoting.

| Ceiling | Limit | What it forces |
|---|---|---|
| **Groq free tier, 70B** | 100,000 tokens/day | ≈ **150 drafted replies/day**. Anything real needs the paid Developer tier. |
| **Groq free tier, 8B** | 500,000 tokens/day | ≈ 1,250 triages/day |
| **Groq free tier RPM** | 30 req/min | ≈ 15 emails/min end-to-end |
| **Gmail send, Workspace** | 2,000 recipients/day | 1 extra mailbox per additional 2,000 replies/day |
| **Gmail send, free @gmail.com** | 500/day | not viable for production |
| **Cold outbound deliverability** | ~30–50 sends/day/mailbox is the safe practical rate for *cold* mail | multiple domains + mailboxes; this is an outreach-infra cost the code does not model |

The last row matters: this product **replies** to inbound mail, which is not rate-shaped like cold
outreach. But if a client asks it to also send cold sequences, mailbox count — not tokens — becomes
the dominant cost.

---

## 7. Costs the code creates for no reason (fix these before quoting)

1. **ChromaDB is a dead dependency.** `chromadb`, `onnxruntime`, `kubernetes`, `tokenizers`,
   `huggingface_hub`, `numpy`, the whole OpenTelemetry set — ~40 of the ~95 lines in
   `requirements.txt` — exist only so `selfcheck.py:109` can print `[OK] ChromaDB reachable`.
   No RAG is implemented anywhere. Removing them shrinks the backend image roughly 1.2 GB → 250 MB
   and drops resident RAM ~350 MB, which is the difference between a Render **Starter ($7)** and
   **Standard ($25)** instance: **$18/mo saved, or a smaller VPS.**
2. **`gcal/` does not exist.** `api/meetings.py:12` imports `from gcal.client import insert_event`.
   The module is not in the repo and not in `git ls-files`. Calendar booking will raise on import —
   the "meeting booking" feature is not shippable today. Cost impact is $0 (Calendar API is free),
   but do not sell it as working.
3. **Apollo is stubbed.** The "lead sourcing" feature reads a fixture file. `APOLLO_API_KEY` is
   defined in config and never used.
4. **`GMAIL_POLL_INTERVAL_MS=1500` is a lie** — `poller.py:78` clamps to a 5 s floor. Harmless, but
   the demo claims 1.5 s responsiveness it does not deliver.

---

## 8. Total monthly cost — four scenarios

Assumes Groq paid Developer tier, one Workspace Business Starter mailbox (~$3.20), $1/mo domain.

### S1 — Pilot / one small client
300 inbound emails, 150 chats × 6 turns

| Line | Cost |
|---|---|
| Groq (emails) | $0.14 |
| Groq (chat, 900 turns) | $0.46 |
| Hosting (Hetzner VPS) | $5.20 |
| Mailbox + domain | $4.20 |
| Apollo | $0 (stub) |
| **Total** | **≈ $10/mo** |

### S2 — Active SMB
2,000 inbound emails, 800 chats × 8 turns

| Line | VPS | Render |
|---|---|---|
| Groq (emails) | $0.90 | $0.90 |
| Groq (chat, 6,400 turns) | $3.24 | $3.24 |
| Hosting | $5.20 | $38.00 |
| Mailbox + domain | $4.20 | $4.20 |
| **Total** | **≈ $14/mo** | **≈ $46/mo** |

### S3 — Agency, real lead sourcing
20,000 inbound emails, 6,000 chats × 8 turns, 2 mailboxes, Apollo Professional 1 seat

| Line | Cost |
|---|---|
| Groq (emails) | $9.00 |
| Groq (chat, 48,000 turns) | $24.29 |
| Hosting (Render managed) | $38.00 |
| Mailboxes (2) + domain | $7.40 |
| Apollo Professional | $79.00 |
| **Total** | **≈ $158/mo** |

With `FAST_FALLBACK=true` the Groq lines collapse to $0.35 + $2.15 → **≈ $127/mo**.

### S4 — High volume
100,000 inbound emails, 30,000 chats × 10 turns

| Line | Cost |
|---|---|
| Groq (emails) | $45.00 |
| Groq (chat, 300,000 turns) | $151.80 |
| Hosting (Hetzner CX43 8 vCPU/16 GB or Render Pro) | $20–60 |
| Mailboxes (needs ≥1 per 2,000 sends/day → 2) + domain | $7.40 |
| Apollo Organization (3-seat min) | $357.00 |
| **Total** | **≈ $580–620/mo** (or ≈ $415 with 8B fallback, no Apollo: ≈ $250) |

---

## 9. Quoting formula

Give a client these five numbers and you have their price:

```
E  = inbound emails/month
C  = chat conversations/month
T  = avg turns per conversation
M  = mailboxes needed = ceil(daily_sends / 2000)
A  = Apollo seats (0 if using bundled data)

monthly_usd =
    0.00045 * E                    # triage + draft, 70B
  + 0.000506 * C * T               # chat turns, 70B
  + hosting                        # 5.20 VPS | 38 Render | 51 Vercel+Render
  + 3.20 * M                       # Workspace Business Starter
  + 1.00                           # domain
  + 79 * A                         # Apollo Professional
```

With `GROQ_MODEL_DRAFT_FAST_FALLBACK=true`, swap the first two coefficients for
`0.000060 * E` and `0.0000447 * C * T`.

**Rules of thumb that fall out of this:**

- Below ~5,000 emails + 40,000 chat turns/month, **LLM cost is under $25 and hosting dominates.**
- Apollo, if the client wants real leads, is **half the bill** at every volume under ~50k ops/month.
- The AI itself is the *cheapest* part of this product. Anyone quoting "AI is expensive" for this
  stack is wrong by an order of magnitude — Groq at these token counts is fractions of a cent per lead.
- The floor for a working single-client deployment is **≈ $10/mo**. The floor for a managed,
  no-ops deployment with real lead data is **≈ $130/mo**.

---

## Sources

- [Groq pricing](https://groq.com/pricing) — retrieved 2026-07-27
- [Groq rate limits](https://console.groq.com/docs/rate-limits)
- [Gmail API usage limits](https://developers.google.com/workspace/gmail/api/reference/quota)
- [Google Workspace pricing (India)](https://workspace.google.com/pricing)
- [Apollo.io pricing](https://www.apollo.io/pricing) + [2026 plan breakdown](https://www.saleshandy.com/blog/apolloio-pricing/)
- [Render pricing](https://render.com/pricing) + [2026 tier breakdown](https://kuberns.com/blogs/render-postgres-pricing-setup-limits/)
- [Hetzner Cloud cost-optimized plans](https://www.hetzner.com/cloud/cost-optimized/) + [July 2026 prices](https://comparedge.com/tools/hetzner/pricing)
- [Vercel pricing](https://vercel.com/pricing)
