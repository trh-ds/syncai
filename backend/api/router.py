from fastapi import APIRouter, Request
from starlette.responses import RedirectResponse, JSONResponse

from gmail.oauth import get_auth_url, exchange_code, _save_refresh_token

router = APIRouter()


@router.get("/auth/start")
async def auth_start():
    return RedirectResponse(get_auth_url())


@router.get("/auth/callback")
async def auth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return JSONResponse({"error": "no code"}, status_code=400)

    try:
        token_data = await exchange_code(code)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    refresh_token = token_data.get("refresh_token")
    access_token = token_data.get("access_token")

    if refresh_token:
        _save_refresh_token(refresh_token)

    return JSONResponse({
        "refresh_token": refresh_token,
        "access_token": access_token,
        "token_type": token_data.get("token_type"),
        "expires_in": token_data.get("expires_in"),
    })


@router.get("/health")
async def health():
    return {"status": "ok"}
