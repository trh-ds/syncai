import json
import os
import urllib.parse

from google.oauth2.credentials import Credentials

from config import settings

REDIRECT_URI = "http://localhost:8000/auth/callback"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.events",
    "openid",
    "email",
    "profile",
]


def get_auth_url() -> str:
    params = {
        "client_id": settings.gcp_client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    return "https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode(params)


async def exchange_code(code: str) -> dict:
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.gcp_client_id,
                "client_secret": settings.gcp_client_secret,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()


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
