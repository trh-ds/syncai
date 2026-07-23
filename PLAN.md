Here is the complete, detailed Markdown blueprint. You can use this as a master prompt for an AI coding assistant (like Cursor or GitHub Copilot) or as a personal project specification document to build the MVP from scratch.

```markdown
# Project Blueprint: Autonomous SDR & Ops Router (ASDR)

## 1. Project Overview
The ASDR is a B2B SaaS MVP designed to automate inbound email triage, lead qualification, and response generation for US-based SMBs. It captures incoming emails, uses Agentic AI to classify intent and extract data, queries a client-specific knowledge base (RAG) to draft highly personalized replies, and stores everything for human approval. (CRM updates and Slack notifications are Phase 5, post-sale.)

**Value Proposition:** Reduces operational costs by eliminating manual email triage and increases revenue through sub-second speed-to-lead response times.

## 2. Tech Stack (locked decisions)
*   **Frontend:** Next.js (App Router) with React and TypeScript. Tailwind CSS for styling. Shadcn UI for components.
*   **Backend & AI Server:** Python with FastAPI.
*   **Agentic AI Framework:** Raw Groq SDK + Pydantic for strict JSON validation. (No LangChain — the "agents" are 3 prompt calls; LangChain adds dependency weight for zero benefit at MVP scale.)
*   **LLM Provider:** Groq, model `llama-3.3-70b-versatile` via env var `GROQ_MODEL`. (Plan's original "Llama-3-70B / Mixtral-8x7B" names are deprecated on Groq.)
*   **Vector Database (RAG):** ChromaDB, running in-process inside the backend container. (No Pinecone — no external account/API key needed for one mock knowledge base.)
*   **Relational Database:** PostgreSQL running locally in Docker Compose, accessed via SQLAlchemy ORM. (Note: SQLAlchemy is the ORM, Postgres is the DB — they are used together, not alternatives. No Supabase for MVP.)
*   **Auth / Tenancy:** None. Single-tenant demo (one hardcoded client). Dashboard and `/demo` are open at the URL. Real login + multi-tenancy is post-sale work.
*   **DevOps:** Docker, Docker Compose, GitHub Actions (CI/CD). Frontend on Vercel, backend on Render.

---

## 3. System Design & Architecture

### High-Level Data Flow
1. **Ingestion:** An inbound email hits the client's inbox (Gmail/Outlook). An App-Specific Password or API token triggers a webhook to our Python FastAPI backend.
2. **Triage & Extraction:** The FastAPI server receives the raw email payload. It sends the email body to the Groq LLM with a strict system prompt to extract JSON: `{"intent": "Sales/Support/Spam", "sender_name": "...", "company": "...", "summary": "..."}`.
3. **RAG Context Retrieval:** If intent is "Sales" or "Support", the backend queries the local ChromaDB instance using the email content to retrieve relevant company policies, pricing, or case studies.
4. **Draft Generation:** The backend sends the retrieved context + original email to Groq LLM to generate a human-like, on-brand draft response.
5. **Storage:** The extracted data, original email, and AI draft are saved to PostgreSQL. (Slack notification and CRM creation are Phase 5 — post-sale, out of MVP scope.)
6. **Dashboard:** The Next.js frontend fetches this data from the FastAPI backend via REST API, displaying the drafts in a Kanban-style board for the client to "Approve", "Edit", or "Send".

### DevOps & Infrastructure
*   **Containerization:** The Python backend and Next.js frontend are containerized using Docker. A `docker-compose.yml` file will orchestrate the frontend, backend, and a local PostgreSQL DB for development.
*   **Environment Management:** `.env` files manage API keys (Groq, DB URLs, client company name). Never commit `.env` files.
*   **Hosting Strategy:** 
    *   Frontend: Vercel (for instant global edge deployment).
    *   Backend: Render. (AWS ECS is overkill for MVP webhook volume.)
*   **CI/CD:** GitHub Actions pipeline that lints TypeScript, runs Python tests, builds Docker images, and deploys on push to the `main` branch.

---

## 4. Folder Structure

The project will use a monorepo structure for easy management.

```text
/asdr-mvp
├── /frontend                  # Next.js Application
│   ├── /app
│   │   ├── /api               # Next.js API routes (if proxying needed)
│   │   ├── /dashboard         # Main UI for viewing drafts
│   │   ├── /demo              # Public demo page (paste URL + sample email → live draft)
│   │   ├── layout.tsx
│   │   └── page.tsx           # Landing/Login page
│   ├── /components
│   │   ├── /ui                # Shadcn UI components
│   │   ├── EmailCard.tsx      # Component displaying the draft & original email
│   │   └── Navbar.tsx
│   ├── /lib
│   │   ├── api.ts             # Axios/Fetch wrapper for FastAPI backend
│   │   └── utils.ts
│   ├── package.json
│   └── tsconfig.json
│
├── /backend                   # Python FastAPI Application
│   ├── /api
│   │   ├── /v1
│   │   │   ├── endpoints.py   # CRUD for emails, settings
│   │   │   └── webhooks.py    # Inbound email webhook receiver
│   ├── /core
│   │   ├── config.py          # Pydantic settings (env vars)
│   │   └── database.py        # SQLAlchemy/Postgres connection
│   ├── /agents
│   │   ├── triage_agent.py    # LLM logic for intent extraction
│   │   ├── rag_agent.py       # ChromaDB retrieval logic (raw SDK, no LangChain)
│   │   └── draft_agent.py     # LLM logic for final email draft generation
│   ├── /models
│   │   └── email.py           # Pydantic models for DB schema
│   ├── main.py                # FastAPI entry point
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml         # Orchestrates Frontend, Backend, DB
└── README.md
```

---

## 5. Application Planning & Demo Strategy

The goal is to build a "Demo Ready" state. When pitching to a US client, you will send them a hosted link. The demo will simulate an inbound email and show the AI generating a draft in real-time.

### Phase 1: Backend & AI Core (Days 1-3)
1. Initialize FastAPI app. Set up `/webhooks/email` endpoint.
2. Create a mock email sender script (or use a tool like Postman) to send JSON payloads mimicking Gmail/Outlook webhooks.
3. Implement `triage_agent.py`: Connect to Groq API. Write a system prompt that forces the LLM to output strict JSON classifying the email. (e.g., `{"intent": "Sales", "summary": "Wants SEO pricing"}`).
4. Implement `rag_agent.py`: Create a mock knowledge base text file (e.g., "Apex Digital Pricing: $3000 for web design"). Chunk it, embed it, and store in a local ChromaDB instance. Write a retriever function.

### Phase 2: Draft Generation & Database (Days 4-5)
1. Implement `draft_agent.py`: Combine the original email, the triage JSON, and the RAG context. Prompt Groq Llama-3 to write the final email reply.
2. Set up PostgreSQL schema: `Emails` table (id, sender, subject, body, ai_draft, status [pending, approved, sent]).
3. Connect FastAPI to Postgres. Save incoming emails and AI drafts automatically.

### Phase 3: Frontend Dashboard (Days 6-8)
1. Initialize Next.js with Tailwind and Shadcn UI.
2. Build a simple Dashboard page fetching `/api/v1/emails?status=pending`.
3. Build the `EmailCard` component: Displays sender info, original email, and the AI draft in a text area (so the user can edit it).
4. Add "Approve & Send" and "Discard" buttons (mock the send functionality for the MVP).

### Phase 4: Demo Preparation & Deployment (Days 9-10)
*Crucial for pitching:* You need to show the client the system working *with their data* before they buy.
1. **The Demo Mode:** Create a page in the Next.js app called `/demo`. 
2. On this page, include a form where the client can paste their company URL and a sample inbound email.
3. When they click "Run Demo", the backend scrapes their URL (using a simple BeautifulSoup script or just passes the URL as context), runs the Groq LLM to draft a response, and returns it to the UI within 3 seconds.
4. **Deploy:** Push frontend to Vercel, backend to Render. Ensure environment variables are securely set.

### Phase 5: Integrations (Post-Sale / Post-Demo — OUT OF MVP SCOPE)
Once a client signs off on the demo, you wire up the actual integrations: Gmail API for ingestion, Slack webhooks for notifications, HubSpot API for CRM creation, plus real auth/multi-tenancy. Not built in this MVP.

---

## 6. Core AI Prompts (For your reference)

**Triage Agent System Prompt:**
```text
You are an expert sales operations assistant. Read the provided email. 
Extract the intent, sender name, and a 1-sentence summary.
Output strictly in JSON format:
{"intent": "[Sales Lead / Customer Support / Spam / Other]", "sender_name": "[Name]", "summary": "[1 sentence summary]"}
```

**Draft Agent System Prompt:**
```text
You are a helpful, professional Account Executive at [Client Company Name].
A prospective lead has emailed you. 
Here is the lead's email: {original_email}
Here is relevant information from your company's knowledge base: {rag_context}

Write a concise, friendly, and highly personalized reply to the lead. Address their specific pain points using the knowledge base context. Do not sound robotic or use generic sales jargon. Include a call to action to book a meeting.
```

## 7. Next Steps to Execute
1. Run `npx create-next-app@latest frontend --typescript --tailwind --app`
2. Run `python -m venv venv` and initialize FastAPI in the `/backend` folder.
3. Set up the `docker-compose.yml` file to ensure both services can talk to each other locally.
4. Build Phase 1 (Backend & Groq API integration) first to prove the AI can generate the drafts accurately.
```

### How to use this MD:
1. **As a Prompt:** Paste this entire markdown file into an AI IDE like Cursor or Windsurf. Tell it: *"Read this blueprint. Let's start with Phase 1: Backend & AI Core. Create the FastAPI folder structure and implement the Groq API integration for the triage agent."*
2. **For the Demo Pitch:** Once you complete Phase 4, you will have a live URL. You email the prospect: *"I built an AI system tailored for B2B service businesses. Go to [Your Vercel Link]/demo, paste a sample customer email you usually struggle to answer quickly, and watch it draft a perfect reply in 2 seconds."*