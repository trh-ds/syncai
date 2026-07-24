from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agents import rag_agent
from api.v1 import billing, calendar_routes, chat, compliance_routes, crm, endpoints, onboarding, settings, webhooks
from core.config import settings as app_settings
from core.database import init_db
from services.mail_poller import poller


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    rag_agent.seed_if_empty()
    await poller.start()
    yield
    await poller.stop()


app = FastAPI(title="ASDR Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": str(exc.errors())}},
    )


@app.exception_handler(HTTPException)
async def http_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        return JSONResponse(status_code=exc.status_code, content={"error": detail})
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "ERROR", "message": str(detail)}},
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": str(exc)}})


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(endpoints.router, prefix="/api/v1")
app.include_router(settings.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(calendar_routes.router, prefix="/api/v1")
app.include_router(crm.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(onboarding.router, prefix="/api/v1")
app.include_router(compliance_routes.router, prefix="/api/v1")
