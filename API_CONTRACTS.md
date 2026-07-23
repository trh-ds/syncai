# API Contracts

- Base URL: `http://localhost:8000` (backend), frontend calls via `NEXT_PUBLIC_API_URL`
- Auth: none (single-tenant demo)
- All timestamps: ISO 8601 UTC
- Error shape (all endpoints): `{ "error": { "code": "STRING", "message": "..." } }`

---

## GET /health
**Response 200**: `{ "status": "ok" }`

---

## POST /api/v1/webhooks/email
Simulates an inbound email. Runs triage → RAG → draft, persists, returns the created record.

**Request**:
```json
{
  "sender": "jane@acme.com",
  "subject": "Pricing question",
  "body": "Hi, what does a website redesign cost?"
}
```

**Response 201**:
```json
{
  "id": "uuid",
  "sender": "jane@acme.com",
  "sender_name": "Jane",
  "subject": "Pricing question",
  "body": "Hi, what does a website redesign cost?",
  "intent": "Sales",
  "summary": "Wants pricing for a website redesign.",
  "ai_draft": "Hi Jane, ...",
  "status": "pending",
  "created_at": "2026-07-21T00:00:00Z",
  "updated_at": "2026-07-21T00:00:00Z"
}
```
Notes: `intent` ∈ `Sales | Support | Spam | Other`. Spam/Other → `ai_draft` is `null`. `sender_name` may be `null`.
`gmail_message_id` and `gmail_thread_id` are set when ingested via Gmail polling.

### Response 502 (LLM error or Groq API key missing)
```json
{ "error": { "code": "LLM_ERROR", "message": "..." } }
```

---

## GET /api/v1/settings
**Response 200**:
```json
{
  "mail_mode": "hitl",
  "poll_interval": 30,
  "gmail_configured": true,
  "gmail_user": "you@gmail.com"
}
```

## PATCH /api/v1/settings
Toggle mail bot mode between `auto` (send replies immediately) and `hitl` (draft, wait for approval).

**Request**:
```json
{ "mail_mode": "auto" }
```

**Response 200**: same shape as GET.

---

## GET /api/v1/emails?status=pending
`status` optional, ∈ `pending | approved | discarded | sent`. Omit for all.

**Response 200**: array of email objects (same shape as above), newest first.

---

## GET /api/v1/emails/{id}
**Response 200**: email object. **404**: `{ "error": { "code": "NOT_FOUND", ... } }`

---

## PATCH /api/v1/emails/{id}
Edit draft and/or transition status. "Approve & Send" = `status: "approved"` (no real sending in MVP).

**Request** (both fields optional, at least one required):
```json
{ "ai_draft": "edited text", "status": "approved" }
```

**Response 200**: updated email object.
**422**: invalid status value, empty body, or transition from non-pending status. Only `"approved"` and `"discarded"` are allowed targets from `"pending"`.

---

## POST /api/v1/demo/run
Public demo. Scrapes `url` for context, drafts a reply to `email_body`. Nothing persisted.

**Request**:
```json
{
  "url": "https://example.com",
  "sender_name": "John",
  "email_body": "Do you offer SEO services?"
}
```

**Response 200**:
```json
{ "draft": "Hi John, ...", "context_used": "Example Corp offers..." }
```
**502**: `{ "error": { "code": "SCRAPE_FAILED", ... } }` if URL unreachable.
