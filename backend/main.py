from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.router import router as auth_router
from api.meetings import router as meetings_router
from api.chat import router as chat_router
from api.leads import router as leads_router
from api.activity import router as activity_router
from api.metrics import router as metrics_router
from gmail.poller import gmail_poller
from db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    import asyncio
    task = asyncio.create_task(gmail_poller())
    yield
    task.cancel()

app = FastAPI(title="ASDR Demo", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(meetings_router)
app.include_router(chat_router)
app.include_router(leads_router)
app.include_router(activity_router)
app.include_router(metrics_router)
