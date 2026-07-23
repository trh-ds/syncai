from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    DATABASE_URL: str = "postgresql+psycopg://asdr:asdr@localhost:5432/asdr"
    CLIENT_COMPANY_NAME: str = "Apex Digital"
    CHROMA_PATH: str = "./chroma_data"
    KB_SEED_FILE: str = "./mock_kb.txt"
    CORS_ORIGINS: str = "http://localhost:3000"

    # Gmail OAuth
    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    GMAIL_REFRESH_TOKEN: str = ""
    GMAIL_USER_EMAIL: str = ""

    # Mail bot
    MAIL_MODE: str = "hitl"  # "auto" | "hitl"
    MAIL_POLL_INTERVAL: int = 30  # seconds

    # Chatbot
    CHATBOT_URL: str = "http://localhost:3000/chat"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def gmail_configured(self) -> bool:
        return bool(self.GMAIL_CLIENT_ID and self.GMAIL_CLIENT_SECRET and self.GMAIL_REFRESH_TOKEN)

    def require_groq_key(self) -> str:
        key = self.GROQ_API_KEY.strip()
        if not key or "placeholder" in key.lower() or key.endswith("..."):
            raise RuntimeError(
                "GROQ_API_KEY is missing or a placeholder. Set a real key in backend/.env"
            )
        return key


settings = Settings()
