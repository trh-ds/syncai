import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from db.session import get_db
from events import subscribe
from models import ActivityEvent
from schemas import ActivityEventOut

router = APIRouter(prefix="/api/activity", tags=["activity"])


@router.get("/", response_model=list[ActivityEventOut])
async def list_activity(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ActivityEvent)
        .order_by(ActivityEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    events = result.scalars().all()
    return [ActivityEventOut.model_validate(e) for e in events]


@router.get("/stream")
async def activity_stream():
    async def generate():
        async for event in subscribe():
            yield f"data: {json.dumps(event, default=str)}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
