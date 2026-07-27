from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Groq
    groq_api_key: str = ""
    groq_model_triage: str = "llama-3.1-8b-instant"
    groq_model_draft: str = "llama-3.3-70b-versatile"
    groq_model_draft_fast_fallback: bool = False

    # Google OAuth
    gcp_client_id: str = ""
    gcp_client_secret: str = ""
    gmail_refresh_token: str = ""
    gmail_monitored_email: str = ""
    gmail_prospect_email: str = ""
    gmail_poll_interval_ms: int = 1500

    # Google Calendar
    google_calendar_id: str = "primary"

    # Apollo
    apollo_api_key: str = ""
    apollo_saved_query_json: str = '{}'

    # Postgres
    database_url: str = "postgresql+psycopg://asdr:asdr@localhost:5432/asdr_demo"

    # Demo
    demo_lead_id: str = ""

    # Misc
    cors_origins: str = "http://localhost:3000"
    chat_working_hours: str = "09:00-18:00"
    chat_tz: str = "Asia/Kolkata"


settings = Settings()
