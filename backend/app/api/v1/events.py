from fastapi import APIRouter, Depends, UploadFile, File, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.dependencies import get_current_user
from app.core.exceptions import ValidationError
from app.db.session import get_db
from app.models.user import User
from app.schemas.event import (
    EventCreate, BatchEventCreate, EventOut, EventQueryParams,
    AggregationResult, SavedQueryCreate, SavedQueryOut,
)
from app.services.event_service import EventService
from app.models.event import SavedQuery
from sqlalchemy import select

router = APIRouter(prefix="/events", tags=["Data Ingestion"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/ingest", response_model=EventOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("500/minute")
async def ingest_single(
    request: Request,
    data: EventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ingest a single event."""
    event = await EventService.ingest_single(db, current_user.org_id, data)
    return EventOut.model_validate(event)



@router.post("/ingest/batch", status_code=status.HTTP_201_CREATED)
@limiter.limit("100/minute")
async def ingest_batch(
    request: Request,
    data: BatchEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ingest a batch of events (up to 1000)."""
    count = await EventService.ingest_batch(db, current_user.org_id, data)
    return {"ingested": count}


@router.post("/ingest/csv", status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def ingest_csv(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a CSV file for bulk event ingestion."""
    if not file.filename or not file.filename.endswith(".csv"):
        raise ValidationError("Only CSV files are supported", details={"filename": file.filename})
    content = await file.read()
    count = await EventService.ingest_csv(db, current_user.org_id, content)
    return {"ingested": count}


@router.get("/query", response_model=AggregationResult)
async def query_events(
    event_name: str | None = None,
    time_range: str = "7d",
    aggregation: str = "count",
    group_by: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query events with time-bucketed aggregation (count, sum, avg, unique)."""
    return await EventService.query_events(
        db, current_user.org_id,
        event_name=event_name,
        time_range=time_range,
        aggregation=aggregation,
        group_by=group_by,
    )


@router.get("/names", response_model=list[str])
async def list_event_names(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all distinct event names for the organization."""
    return await EventService.list_event_names(db, current_user.org_id)


@router.get("/recent", response_model=list[EventOut])
async def recent_events(
    limit: int = Query(default=50, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the most recent events (default 50, max 200)."""
    events = await EventService.get_recent_events(db, current_user.org_id, limit)
    return [EventOut.model_validate(e) for e in events]


# ─── Saved Queries ───────────────────────────────
@router.post("/queries", response_model=SavedQueryOut, status_code=status.HTTP_201_CREATED)
async def create_saved_query(
    data: SavedQueryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sq = SavedQuery(
        org_id=current_user.org_id,
        name=data.name,
        event_name=data.event_name,
        aggregation=data.aggregation,
        group_by=data.group_by,
        filters=data.filters,
        time_range=data.time_range,
        created_by=current_user.id,
    )
    db.add(sq)
    await db.flush()
    return SavedQueryOut.model_validate(sq)


@router.get("/queries", response_model=list[SavedQueryOut])
async def list_saved_queries(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SavedQuery).where(SavedQuery.org_id == current_user.org_id)
    )
    return [SavedQueryOut.model_validate(q) for q in result.scalars().all()]


# ─── Webhook Receiver ────────────────────────────
@router.post("/ingest/webhook", status_code=status.HTTP_201_CREATED)
@limiter.limit("100/minute")
async def ingest_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook receiver for external event ingestion.
    Expects JSON body with 'events' array and 'api_key' header.
    """
    from app.models.event import Event
    from app.models.user import APIKey
    from app.core.security import verify_password

    # Authenticate via API key header
    api_key_raw = request.headers.get("X-API-Key", "")
    if not api_key_raw:
        raise ValidationError("Missing X-API-Key header")

    # Find matching key
    result = await db.execute(select(APIKey).where(APIKey.is_active == True))
    api_keys = result.scalars().all()
    matched_key = None
    for key in api_keys:
        if api_key_raw.startswith(key.key_prefix):
            if verify_password(api_key_raw, key.key_hash):
                matched_key = key
                break

    if not matched_key:
        raise ValidationError("Invalid API key")

    # Parse body
    body = await request.json()
    events_data = body if isinstance(body, list) else body.get("events", [body])

    count = 0
    for e in events_data:
        if not isinstance(e, dict) or "name" not in e:
            continue
        event = Event(
            org_id=matched_key.org_id,
            name=e["name"],
            source="webhook",
            properties={k: v for k, v in e.items() if k not in ("name", "event_name")},
        )
        db.add(event)
        count += 1

    await db.flush()

    # Update last used timestamp
    from datetime import datetime, timezone
    matched_key.last_used_at = datetime.now(timezone.utc)

    return {"ingested": count, "source": "webhook"}
