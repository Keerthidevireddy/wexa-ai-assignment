"""Tests for all event ingestion and query endpoints.

Endpoints tested:
  POST /events/ingest       - Single event ingestion
  POST /events/ingest/batch - Batch event ingestion
  POST /events/ingest/csv   - CSV file upload
  GET  /events/query        - Time-bucketed aggregation
  GET  /events/names        - List distinct event names
  GET  /events/recent       - Recent events
  POST /events/queries      - Save a query
  GET  /events/queries      - List saved queries
"""

import io
import pytest
from httpx import AsyncClient
from tests.conftest import create_test_user


# ════════════════════════════════════════════════
#  SINGLE EVENT INGESTION
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ingest_single_event(client: AsyncClient):
    """POST /events/ingest — ingest a single event returns 201."""
    user = await create_test_user(client, "ingest1@test.com")
    response = await client.post("/api/v1/events/ingest", json={
        "name": "page_view",
        "properties": {"page": "/home", "browser": "chrome"},
        "user_id": "user_1",
    }, headers=user["headers"])
    assert response.status_code == 201, f"Got {response.status_code}: {response.text}"
    data = response.json()
    assert data["name"] == "page_view"
    assert data["source"] == "api"
    assert data["properties"]["page"] == "/home"
    assert data["org_id"] == user["user"]["org_id"]


@pytest.mark.asyncio
async def test_ingest_event_without_auth(client: AsyncClient):
    """POST /events/ingest — no auth returns 401 or 403."""
    response = await client.post("/api/v1/events/ingest", json={
        "name": "test_event",
    })
    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_ingest_event_validation(client: AsyncClient):
    """POST /events/ingest — missing name field returns 422."""
    user = await create_test_user(client, "ingest_val@test.com")
    response = await client.post("/api/v1/events/ingest", json={
        "properties": {"page": "/home"},
    }, headers=user["headers"])
    assert response.status_code == 422


# ════════════════════════════════════════════════
#  BATCH INGESTION
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ingest_batch_events(client: AsyncClient):
    """POST /events/ingest/batch — batch returns count."""
    user = await create_test_user(client, "batch@test.com")
    response = await client.post("/api/v1/events/ingest/batch", json={
        "events": [
            {"name": "click", "properties": {"button": "cta"}},
            {"name": "click", "properties": {"button": "nav"}},
            {"name": "signup", "properties": {}},
        ]
    }, headers=user["headers"])
    assert response.status_code == 201
    assert response.json()["ingested"] == 3


@pytest.mark.asyncio
async def test_ingest_batch_empty(client: AsyncClient):
    """POST /events/ingest/batch — empty batch returns 422."""
    user = await create_test_user(client, "batch_empty@test.com")
    response = await client.post("/api/v1/events/ingest/batch", json={
        "events": []
    }, headers=user["headers"])
    assert response.status_code == 422  # min_length=1


# ════════════════════════════════════════════════
#  CSV INGESTION
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ingest_csv(client: AsyncClient):
    """POST /events/ingest/csv — CSV upload ingests events."""
    user = await create_test_user(client, "csv@test.com")
    csv_content = "event_name,page,browser\npage_view,/home,chrome\nclick,/about,firefox\n"
    response = await client.post(
        "/api/v1/events/ingest/csv",
        files={"file": ("events.csv", csv_content, "text/csv")},
        headers=user["headers"],
    )
    assert response.status_code == 201, f"Got {response.status_code}: {response.text}"
    assert response.json()["ingested"] == 2


# ════════════════════════════════════════════════
#  QUERY EVENTS
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_query_events(client: AsyncClient):
    """GET /events/query — aggregation returns labels, values, total."""
    user = await create_test_user(client, "query@test.com")
    
    # Ingest some events first
    for i in range(5):
        await client.post("/api/v1/events/ingest", json={
            "name": "page_view",
            "properties": {"page": f"/page_{i}"},
        }, headers=user["headers"])

    response = await client.get("/api/v1/events/query", params={
        "event_name": "page_view",
        "time_range": "7d",
    }, headers=user["headers"])
    assert response.status_code == 200
    data = response.json()
    assert "labels" in data
    assert "values" in data
    assert "total" in data
    assert data["total"] >= 5


@pytest.mark.asyncio
async def test_query_events_without_filter(client: AsyncClient):
    """GET /events/query — no event_name queries all events."""
    user = await create_test_user(client, "query_all@test.com")
    await client.post("/api/v1/events/ingest", json={"name": "ev_a"}, headers=user["headers"])
    await client.post("/api/v1/events/ingest", json={"name": "ev_b"}, headers=user["headers"])

    response = await client.get("/api/v1/events/query", params={
        "time_range": "7d",
    }, headers=user["headers"])
    assert response.status_code == 200
    assert response.json()["total"] >= 2


# ════════════════════════════════════════════════
#  LIST EVENT NAMES
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_event_names(client: AsyncClient):
    """GET /events/names — returns distinct event names."""
    user = await create_test_user(client, "names@test.com")
    await client.post("/api/v1/events/ingest", json={"name": "page_view"}, headers=user["headers"])
    await client.post("/api/v1/events/ingest", json={"name": "signup"}, headers=user["headers"])
    await client.post("/api/v1/events/ingest", json={"name": "purchase"}, headers=user["headers"])

    response = await client.get("/api/v1/events/names", headers=user["headers"])
    assert response.status_code == 200
    names = response.json()
    assert isinstance(names, list)
    assert "page_view" in names
    assert "signup" in names


# ════════════════════════════════════════════════
#  RECENT EVENTS
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_recent_events(client: AsyncClient):
    """GET /events/recent — returns most recent events."""
    user = await create_test_user(client, "recent@test.com")
    for i in range(3):
        await client.post("/api/v1/events/ingest", json={
            "name": f"event_{i}",
        }, headers=user["headers"])

    response = await client.get("/api/v1/events/recent", params={"limit": 10}, headers=user["headers"])
    assert response.status_code == 200
    events = response.json()
    assert len(events) >= 3
    # Verify structure
    assert "id" in events[0]
    assert "name" in events[0]
    assert "created_at" in events[0]


# ════════════════════════════════════════════════
#  SAVED QUERIES
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_saved_query(client: AsyncClient):
    """POST /events/queries — save a query configuration."""
    user = await create_test_user(client, "saved_q@test.com")
    response = await client.post("/api/v1/events/queries", json={
        "name": "Weekly Signups",
        "event_name": "signup",
        "aggregation": "count",
        "time_range": "7d",
    }, headers=user["headers"])
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Weekly Signups"
    assert data["event_name"] == "signup"


@pytest.mark.asyncio
async def test_list_saved_queries(client: AsyncClient):
    """GET /events/queries — list saved queries for org."""
    user = await create_test_user(client, "list_q@test.com")
    await client.post("/api/v1/events/queries", json={
        "name": "Q1", "event_name": "ev1", "aggregation": "count", "time_range": "7d",
    }, headers=user["headers"])

    response = await client.get("/api/v1/events/queries", headers=user["headers"])
    assert response.status_code == 200
    queries = response.json()
    assert len(queries) >= 1
