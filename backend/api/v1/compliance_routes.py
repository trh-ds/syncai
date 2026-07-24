from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from core.database import get_db
from services import compliance

router = APIRouter(tags=["compliance"])


def _opt_out_response(customer, token: str):
    if not customer:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "INVALID_TOKEN", "message": "Invalid unsubscribe link"}},
        )
    return {"unsubscribed": True, "email": customer.email}


@router.post("/unsubscribe/{token}")
def unsubscribe_post(token: str, db: Session = Depends(get_db)):
    return _opt_out_response(compliance.opt_out(db, token), token)


@router.get("/unsubscribe/{token}", response_class=HTMLResponse)
def unsubscribe_get(token: str, db: Session = Depends(get_db)):
    """One-click link from email footers (email clients can't POST)."""
    customer = compliance.opt_out(db, token)
    if not customer:
        body = "<h1>Invalid link</h1><p>This unsubscribe link is not valid.</p>"
    else:
        body = f"<h1>You're unsubscribed</h1><p>{customer.email} will no longer receive emails from us.</p>"
    return f"<!doctype html><html><head><title>Unsubscribe</title></head><body>{body}</body></html>"
