from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models import Lead, Meeting, EmailMessage, ActivityEvent, DemoMetricsCache
from schemas import MetricsOut

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/", response_model=MetricsOut)
async def get_metrics(db: AsyncSession = Depends(get_db)):
    cache_result = await db.execute(select(DemoMetricsCache).where(DemoMetricsCache.id == 1))
    cache = cache_result.scalar_one_or_none()

    pipeline_result = await db.execute(
        select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
    )
    pipeline = {row[0] or "unknown": row[1] for row in pipeline_result.all()}

    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    sparkline_result = await db.execute(
        select(
            func.date(ActivityEvent.created_at).label("day"),
            func.count(ActivityEvent.id),
        )
        .where(ActivityEvent.created_at >= cutoff)
        .group_by(func.date(ActivityEvent.created_at))
        .order_by(func.date(ActivityEvent.created_at).asc())
    )
    sparkline = [
        {"date": str(row.day), "count": row.count}
        for row in sparkline_result.all()
    ]

    if cache:
        return MetricsOut(
            leads_count=cache.leads_count,
            meetings_count=cache.meetings_count,
            est_cost_saved=cache.est_cost_saved,
            est_hours_saved=cache.est_hours_saved,
            avg_reply_latency_ms=cache.avg_reply_latency_ms,
            success_rate=cache.success_rate,
            pipeline=pipeline,
            activity_sparkline=sparkline,
        )
    else:
        lead_count_result = await db.execute(select(func.count(Lead.id)))
        meeting_count_result = await db.execute(select(func.count(Meeting.id)))
        lc = lead_count_result.scalar() or 0
        mc = meeting_count_result.scalar() or 0

        return MetricsOut(
            leads_count=lc,
            meetings_count=mc,
            est_cost_saved=0,
            est_hours_saved=0,
            avg_reply_latency_ms=0,
            success_rate=0.0,
            pipeline=pipeline,
            activity_sparkline=sparkline,
        )


@router.post("/recompute", response_model=MetricsOut)
async def recompute_metrics(db: AsyncSession = Depends(get_db)):
    lc_result = await db.execute(select(func.count(Lead.id)))
    leads_count = lc_result.scalar() or 0

    mc_result = await db.execute(select(func.count(Meeting.id)))
    meetings_count = mc_result.scalar() or 0

    lat_result = await db.execute(
        select(func.avg(EmailMessage.reply_latency_ms)).where(
            EmailMessage.direction == "outbound",
            EmailMessage.reply_latency_ms.isnot(None),
        )
    )
    avg_lat = lat_result.scalar()
    avg_reply_latency_ms = int(avg_lat) if avg_lat else 0

    outbound_result = await db.execute(
        select(func.count(EmailMessage.id)).where(EmailMessage.direction == "outbound")
    )
    outbound_replies = outbound_result.scalar() or 0

    est_hours_saved = meetings_count * 0.75 + outbound_replies * 0.25
    est_cost_saved = est_hours_saved * 60
    success_rate = meetings_count / max(leads_count, 1)

    cache = DemoMetricsCache(
        id=1,
        leads_count=leads_count,
        meetings_count=meetings_count,
        est_cost_saved=est_cost_saved,
        est_hours_saved=est_hours_saved,
        avg_reply_latency_ms=avg_reply_latency_ms,
        success_rate=success_rate,
    )
    await db.merge(cache)
    await db.commit()

    pipeline_result = await db.execute(
        select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
    )
    pipeline = {row[0] or "unknown": row[1] for row in pipeline_result.all()}

    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    sparkline_result = await db.execute(
        select(
            func.date(ActivityEvent.created_at).label("day"),
            func.count(ActivityEvent.id),
        )
        .where(ActivityEvent.created_at >= cutoff)
        .group_by(func.date(ActivityEvent.created_at))
        .order_by(func.date(ActivityEvent.created_at).asc())
    )
    sparkline = [
        {"date": str(row.day), "count": row.count}
        for row in sparkline_result.all()
    ]

    return MetricsOut(
        leads_count=leads_count,
        meetings_count=meetings_count,
        est_cost_saved=est_cost_saved,
        est_hours_saved=est_hours_saved,
        avg_reply_latency_ms=avg_reply_latency_ms,
        success_rate=success_rate,
        pipeline=pipeline,
        activity_sparkline=sparkline,
    )
