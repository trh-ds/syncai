import json
import os

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from config import settings


def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.gcp_client_id,
            "client_secret": settings.gcp_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8000/auth/callback"],
        }
    }


def get_oauth_flow(redirect_uri: str, scopes: list[str]) -> Flow:
    return Flow.from_client_config(
        _client_config(),
        scopes=scopes,
        redirect_uri=redirect_uri,
        autogenerate_code_verifier=False,
    )


def _save_refresh_token(token: str):
    try:
        with open(".env", "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []
    found = False
    for i, line in enumerate(lines):
        if line.startswith("GMAIL_REFRESH_TOKEN="):
            lines[i] = f"GMAIL_REFRESH_TOKEN={token}\n"
            found = True
            break
    if not found:
        lines.append(f"GMAIL_REFRESH_TOKEN={token}\n")
    with open(".env", "w") as f:
        f.writelines(lines)


async def get_credentials() -> Credentials:
    creds = Credentials(
        token=None,
        refresh_token=settings.gmail_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.gcp_client_id,
        client_secret=settings.gcp_client_secret,
        scopes=[
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/calendar.events",
        ],
    )

    from google.auth.transport.requests import Request
    import asyncio
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, creds.refresh, Request())

    if creds.refresh_token and creds.refresh_token != settings.gmail_refresh_token:
        _save_refresh_token(creds.refresh_token)

    return creds
