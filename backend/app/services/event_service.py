import csv
import io
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import String, select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set, cache_invalidate

from app.models.event import Event, SavedQuery
from app.schemas.event import EventCreate, BatchEventCreate, AggregationResult


TIME_RANGE_MAP = {
    "1h": timedelta(hours=1),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}


class EventService:

    @staticmethod
    async def ingest_single(db: AsyncSession, org_id: str, data: EventCreate) -> Event:
        event = Event(
            org_id=org_id,
            name=data.name,
            source="api",
            properties=data.properties,
            user_id=data.user_id,
            session_id=data.session_id,
            created_at=data.timestamp or datetime.now(timezone.utc),
        )
        db.add(event)
        await db.flush()
        return event

    @staticmethod
    async def ingest_batch(db: AsyncSession, org_id: str, data: BatchEventCreate) -> int:
        events = [
            Event(
                org_id=org_id,
                name=e.name,
                source="api",
                properties=e.properties,
                user_id=e.user_id,
                session_id=e.session_id,
                created_at=e.timestamp or datetime.now(timezone.utc),
            )
            for e in data.events
        ]
        db.add_all(events)
        await db.flush()
        return len(events)

    @staticmethod
    async def ingest_csv(db: AsyncSession, org_id: str, content: bytes) -> int:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
        count = 0
        for row in reader:
            name = row.pop("event_name", row.pop("name", "unknown"))
            event = Event(
                org_id=org_id,
                name=name,
                source="csv",
                properties=dict(row),
            )
            db.add(event)
            count += 1
        await db.flush()
        return count

    @staticmethod
    async def query_events(
        db: AsyncSession,
        org_id: str,
        event_name: str | None = None,
        time_range: str = "7d",
        aggregation: str = "count",
        group_by: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> AggregationResult:
        # Check Redis cache first
        cached = await cache_get(
            org_id, "query",
            event_name=event_name, time_range=time_range,
            aggregation=aggregation, group_by=group_by,
        )
        if cached:
            return AggregationResult(**cached)

        now = datetime.now(timezone.utc)
        if start is None:
            delta = TIME_RANGE_MAP.get(time_range, timedelta(days=7))
            start = now - delta
        if end is None:
            end = now

        base = select(Event).where(
            Event.org_id == org_id,
            Event.created_at >= start,
            Event.created_at <= end,
        )
        if event_name:
            base = base.where(Event.name == event_name)

        # Time-bucketed aggregation
        # Generate hourly or daily buckets depending on range
        delta = end - start
        if delta <= timedelta(hours=24):
            # Use portable date casting — works with both PG and SQLite
            # We cast to string and truncate to hour level
            bucket = func.substr(func.cast(Event.created_at, String), 1, 13).label("bucket")
        else:
            # Truncate to day level
            bucket = func.substr(func.cast(Event.created_at, String), 1, 10).label("bucket")

        agg_func = func.count(Event.id)
        if aggregation == "unique":
            agg_func = func.count(func.distinct(Event.user_id))

        query = (
            select(bucket, agg_func.label("value"))
            .where(
                Event.org_id == org_id,
                Event.created_at >= start,
                Event.created_at <= end,
            )
            .group_by(bucket)
            .order_by(bucket)
        )
        if event_name:
            query = query.where(Event.name == event_name)

        result = await db.execute(query)
        rows = result.all()

        labels = [str(r[0]) for r in rows]
        values = [float(r[1]) for r in rows]
        total = sum(values)

        agg_result = AggregationResult(labels=labels, values=values, total=total)

        # Cache result for 30 seconds
        await cache_set(
            org_id, "query", agg_result.model_dump(), ttl=30,
            event_name=event_name, time_range=time_range,
            aggregation=aggregation, group_by=group_by,
        )

        return agg_result

    @staticmethod
    async def list_event_names(db: AsyncSession, org_id: str) -> list[str]:
        result = await db.execute(
            select(Event.name).where(Event.org_id == org_id).distinct()
        )
        return [r[0] for r in result.all()]

    @staticmethod
    async def get_recent_events(db: AsyncSession, org_id: str, limit: int = 50) -> list[Event]:
        result = await db.execute(
            select(Event)
            .where(Event.org_id == org_id)
            .order_by(Event.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
