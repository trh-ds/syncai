from fastapi import APIRouter, Request
from starlette.responses import RedirectResponse, JSONResponse

from config import settings
from gmail.oauth import get_oauth_flow, exchange_code

router = APIRouter()

REDIRECT_URI = "http://localhost:8000/auth/callback"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.events",
    "openid",
    "email",
    "profile",
]


@router.get("/auth/start")
async def auth_start():
    flow = get_oauth_flow(REDIRECT_URI, SCOPES)
    url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    return RedirectResponse(url)


@router.get("/auth/callback")
async def auth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return JSONResponse({"error": "no code"}, status_code=400)

    flow = get_oauth_flow(REDIRECT_URI, SCOPES)
    flow.fetch_token(code=code)
    creds = flow.credentials
    refresh_token = creds.refresh_token

    if refresh_token:
        try:
            with open(".env", "r") as f:
                lines = f.readlines()
        except FileNotFoundError:
            lines = []

        found = False
        for i, line in enumerate(lines):
            if line.startswith("GMAIL_REFRESH_TOKEN="):
                lines[i] = f"GMAIL_REFRESH_TOKEN={refresh_token}\n"
                found = True
                break
        if not found:
            lines.append(f"GMAIL_REFRESH_TOKEN={refresh_token}\n")
        with open(".env", "w") as f:
            f.writelines(lines)

    return JSONResponse({
        "refresh_token": refresh_token,
        "email": creds.id_token.get("email") if creds.id_token else None,
    })


@router.get("/health")
async def health():
    return {"status": "ok"}
