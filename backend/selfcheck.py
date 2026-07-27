"""Boot self-check — asserts env, DB, Groq, Gmail OAuth, Calendar, ChromaDB reachable."""
import asyncio
import os
import sys

from dotenv import load_dotenv
load_dotenv()


def check_env():
    required = [
        "GROQ_API_KEY", "GCP_CLIENT_ID", "GCP_CLIENT_SECRET",
        "GMAIL_REFRESH_TOKEN", "DATABASE_URL",
    ]
    missing = []
    for key in required:
        if not os.getenv(key):
            missing.append(key)
    if missing:
        print(f"[WARN] Missing env vars: {', '.join(missing)}")
        print("       Some checks will be skipped.")
    else:
        print("[OK] All required env vars present")
    return bool(missing)


async def check_db():
    try:
        from config import settings
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine(settings.database_url, echo=False)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        print("[OK] Database reachable")
    except Exception as e:
        print(f"[FAIL] Database unreachable: {e}")
        return False
    return True


async def check_groq():
    try:
        from config import settings
        if not settings.groq_api_key:
            print("[SKIP] No GROQ_API_KEY set")
            return True
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)
        models = client.models.list()
        model_ids = [m.id for m in models]
        print(f"[OK] Groq reachable ({len(model_ids)} models available)")
    except Exception as e:
        print(f"[FAIL] Groq unreachable: {e}")
        return False
    return True


async def check_gmail_oauth():
    try:
        from config import settings
        if not settings.gmail_refresh_token or not settings.gcp_client_id:
            print("[SKIP] Gmail OAuth not configured (missing refresh token or client id)")
            return True
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        creds = Credentials(
            token=None,
            refresh_token=settings.gmail_refresh_token,
            client_id=settings.gcp_client_id,
            client_secret=settings.gcp_client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )
        creds.refresh(Request())
        print("[OK] Gmail OAuth access token refreshed")
    except Exception as e:
        print(f"[WARN] Gmail OAuth refresh failed: {e}")
        return False
    return True


async def check_calendar():
    try:
        from config import settings
        if not settings.gmail_refresh_token:
            print("[SKIP] Calendar check skipped (no OAuth)")
            return True
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        creds = Credentials(
            token=None,
            refresh_token=settings.gmail_refresh_token,
            client_id=settings.gcp_client_id,
            client_secret=settings.gcp_client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )
        creds.refresh(Request())
        service = build("calendar", "v3", credentials=creds)
        service.events().list(calendarId="primary", maxResults=1).execute()
        print("[OK] Calendar API reachable")
    except Exception as e:
        print(f"[WARN] Calendar check failed: {e}")
        return False
    return True


async def check_chromadb():
    try:
        import chromadb
        client = chromadb.Client(chromadb.config.Settings(
            anonymized_telemetry=False,
            is_persistent=True,
            persist_directory="chroma_data",
        ))
        client.heartbeat()
        print("[OK] ChromaDB reachable (embedded)")
    except Exception as e:
        print(f"[FAIL] ChromaDB unreachable: {e}")
        return False
    return True


async def main():
    print("=== ASDR Boot Self-Check ===\n")
    has_missing_env = check_env()
    print()

    results = await asyncio.gather(
        check_db(),
        check_groq(),
        check_gmail_oauth(),
        check_calendar(),
        check_chromadb(),
    )

    failures = sum(1 for r in results if r is False)
    if failures == 0:
        print("\n[PASS] All checks passed.")
        sys.exit(0)
    else:
        print(f"\n[FAIL] {failures} check(s) failed.")
        if has_missing_env:
            print("       Set missing env vars in .env and retry.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
