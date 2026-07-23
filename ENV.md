# Environment Variables

## Backend (`backend/.env`)
| Var | Example | Notes |
|---|---|---|
| GROQ_API_KEY | gsk_... | Required |
| GROQ_MODEL | llama-3.3-70b-versatile | Swappable |
| DATABASE_URL | postgresql+psycopg://asdr:asdr@localhost:5432/asdr | Compose overrides host to `db` |
| CLIENT_COMPANY_NAME | Apex Digital | Used in draft prompt |
| CHROMA_PATH | ./chroma_data | Vector store persistence dir |
| KB_SEED_FILE | ./mock_kb.txt | Mock knowledge base seed |
| CORS_ORIGINS | http://localhost:3000 | Frontend origin |
| GMAIL_CLIENT_ID | ...apps.googleusercontent.com | Google Cloud OAuth client ID |
| GMAIL_CLIENT_SECRET | GOCSPX-... | Google Cloud OAuth client secret |
| GMAIL_REFRESH_TOKEN | 1//... | Run `python scripts/gmail_auth.py` once to get this |
| GMAIL_USER_EMAIL | you@gmail.com | Email to monitor and send from |
| MAIL_MODE | hitl | "auto" = send immediately, "hitl" = draft pending |
| MAIL_POLL_INTERVAL | 30 | Seconds between inbox checks |
| CHATBOT_URL | http://localhost:3000/chat | URL the mail bot directs leads to |

## Frontend (`frontend/.env.local`)
| Var | Example | Notes |
|---|---|---|
| NEXT_PUBLIC_API_URL | http://localhost:8000 | Backend base URL |

## Rules
- Never commit `.env` / `.env.local`. Provide `.env.example` in each app.
- docker-compose injects `DATABASE_URL` with host `db` for the backend service.
