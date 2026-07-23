# Data Models

Single-tenant MVP: one table. Settings live in `.env`, not the DB.

## Table: emails

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | default gen_random_uuid() |
| sender | TEXT NOT NULL | raw from-address |
| sender_name | TEXT NULL | extracted by triage agent |
| subject | TEXT NOT NULL | |
| body | TEXT NOT NULL | |
| intent | TEXT NOT NULL | Sales / Support / Spam / Other |
| summary | TEXT NOT NULL | 1-sentence, from triage |
| ai_draft | TEXT NULL | null for Spam/Other |
| status | TEXT NOT NULL DEFAULT 'pending' | pending / approved / discarded |
| created_at | TIMESTAMPTZ NOT NULL | default now() |
| updated_at | TIMESTAMPTZ NOT NULL | default now(), touch on update |

**Indexes**: `(status)`, `(created_at DESC)` — covers the Kanban query `WHERE status = ? ORDER BY created_at DESC`.

**Status transitions**: pending → approved | discarded. PATCH is the only writer.

## Vector store (not Postgres)
ChromaDB collection `knowledge_base`, persisted to disk inside backend container (`./chroma_data`). Seeded at startup from a mock KB text file if empty. Documents: chunked client pricing/policy text. No metadata schema beyond `source`.
