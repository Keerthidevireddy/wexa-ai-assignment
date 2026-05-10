"""Tests for all alert & notification endpoints.

Endpoints tested:
  POST   /alerts/                       - Create alert rule
  GET    /alerts/                       - List alerts
  GET    /alerts/notifications          - List notifications
  PATCH  /alerts/notifications/{id}/read - Mark read
  GET    /alerts/{id}                   - Get alert detail
  PATCH  /alerts/{id}                   - Update alert
  DELETE /alerts/{id}                   - Delete alert
  POST   /alerts/{id}/mute             - Mute alert
  GET    /alerts/{id}/history           - Alert history
  GET    /health                        - Health check
"""

import pytest
from httpx import AsyncClient
from tests.conftest import create_test_user


# ════════════════════════════════════════════════
#  CREATE ALERT
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_alert(client: AsyncClient):
    """POST /alerts/ — create alert rule returns 201."""
    user = await create_test_user(client, "alert_create@test.com")
    response = await client.post("/api/v1/alerts/", json={
        "name": "High Error Rate",
        "event_name": "error",
        "metric": "count",
        "operator": ">",
        "threshold": 100,
        "window_minutes": 10,
    }, headers=user["headers"])
    assert response.status_code == 201, f"Got {response.status_code}: {response.text}"
    data = response.json()
    assert data["name"] == "High Error Rate"
    assert data["status"] == "active"
    assert data["threshold"] == 100
    assert data["event_name"] == "error"
    assert data["org_id"] == user["user"]["org_id"]


@pytest.mark.asyncio
async def test_create_alert_with_channels(client: AsyncClient):
    """POST /alerts/ — alert with notification channels."""
    user = await create_test_user(client, "alert_chan@test.com")
    response = await client.post("/api/v1/alerts/", json={
        "name": "Slack Alert",
        "event_name": "error",
        "metric": "count",
        "operator": ">",
        "threshold": 50,
        "window_minutes": 5,
        "channels": {"in_app": True, "email": True, "webhook": "https://hooks.slack.com/xxx"},
    }, headers=user["headers"])
    assert response.status_code == 201
    assert response.json()["channels"]["webhook"] == "https://hooks.slack.com/xxx"


# ════════════════════════════════════════════════
#  LIST ALERTS
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_alerts(client: AsyncClient):
    """GET /alerts/ — list returns org alerts."""
    user = await create_test_user(client, "alert_list@test.com")
    await client.post("/api/v1/alerts/", json={
        "name": "A1", "event_name": "e1",
        "metric": "count", "operator": ">", "threshold": 10, "window_minutes": 5,
    }, headers=user["headers"])
    await client.post("/api/v1/alerts/", json={
        "name": "A2", "event_name": "e2",
        "metric": "count", "operator": "<", "threshold": 3, "window_minutes": 60,
    }, headers=user["headers"])

    response = await client.get("/api/v1/alerts/", headers=user["headers"])
    assert response.status_code == 200
    assert len(response.json()) >= 2


# ════════════════════════════════════════════════
#  GET ALERT DETAIL
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_alert_detail(client: AsyncClient):
    """GET /alerts/{id} — returns alert details."""
    user = await create_test_user(client, "alert_get@test.com")
    create = await client.post("/api/v1/alerts/", json={
        "name": "Detail Alert", "event_name": "ev",
        "metric": "count", "operator": ">", "threshold": 1, "window_minutes": 1,
    }, headers=user["headers"])
    alert_id = create.json()["id"]

    response = await client.get(f"/api/v1/alerts/{alert_id}", headers=user["headers"])
    assert response.status_code == 200
    assert response.json()["name"] == "Detail Alert"


@pytest.mark.asyncio
async def test_get_alert_not_found(client: AsyncClient):
    """GET /alerts/{id} — non-existent returns 404."""
    user = await create_test_user(client, "alert_404@test.com")
    response = await client.get("/api/v1/alerts/fake-id", headers=user["headers"])
    assert response.status_code == 404


# ════════════════════════════════════════════════
#  UPDATE ALERT
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_update_alert(client: AsyncClient):
    """PATCH /alerts/{id} — update threshold."""
    user = await create_test_user(client, "alert_upd@test.com")
    create = await client.post("/api/v1/alerts/", json={
        "name": "Updatable", "event_name": "ev",
        "metric": "count", "operator": ">", "threshold": 10, "window_minutes": 5,
    }, headers=user["headers"])
    alert_id = create.json()["id"]

    response = await client.patch(f"/api/v1/alerts/{alert_id}", json={
        "threshold": 50,
        "name": "Updated Alert",
    }, headers=user["headers"])
    assert response.status_code == 200
    assert response.json()["threshold"] == 50
    assert response.json()["name"] == "Updated Alert"


# ════════════════════════════════════════════════
#  DELETE ALERT
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_delete_alert(client: AsyncClient):
    """DELETE /alerts/{id} — returns 204 and removes alert."""
    user = await create_test_user(client, "alert_del@test.com")
    create = await client.post("/api/v1/alerts/", json={
        "name": "Temp Alert", "event_name": "e",
        "metric": "count", "operator": ">", "threshold": 1, "window_minutes": 1,
    }, headers=user["headers"])
    alert_id = create.json()["id"]

    response = await client.delete(f"/api/v1/alerts/{alert_id}", headers=user["headers"])
    assert response.status_code == 204

    # Verify deleted
    get_resp = await client.get(f"/api/v1/alerts/{alert_id}", headers=user["headers"])
    assert get_resp.status_code == 404


# ════════════════════════════════════════════════
#  MUTE ALERT
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_mute_alert(client: AsyncClient):
    """POST /alerts/{id}/mute — mutes and sets muted_until."""
    user = await create_test_user(client, "alert_mute@test.com")
    create = await client.post("/api/v1/alerts/", json={
        "name": "Mutable", "event_name": "e",
        "metric": "count", "operator": ">", "threshold": 1, "window_minutes": 1,
    }, headers=user["headers"])
    alert_id = create.json()["id"]

    response = await client.post(f"/api/v1/alerts/{alert_id}/mute", json={
        "minutes": 60,
    }, headers=user["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "muted"
    assert data["muted_until"] is not None


# ════════════════════════════════════════════════
#  ALERT HISTORY
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_alert_history(client: AsyncClient):
    """GET /alerts/{id}/history — initially empty."""
    user = await create_test_user(client, "alert_hist@test.com")
    create = await client.post("/api/v1/alerts/", json={
        "name": "History Alert", "event_name": "ev",
        "metric": "count", "operator": ">", "threshold": 1, "window_minutes": 1,
    }, headers=user["headers"])
    alert_id = create.json()["id"]

    response = await client.get(f"/api/v1/alerts/{alert_id}/history", headers=user["headers"])
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ════════════════════════════════════════════════
#  NOTIFICATIONS
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_notifications(client: AsyncClient):
    """GET /alerts/notifications — returns notifications list."""
    user = await create_test_user(client, "notif@test.com")
    response = await client.get("/api/v1/alerts/notifications", headers=user["headers"])
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ════════════════════════════════════════════════
#  HEALTH CHECK
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """GET /health — returns healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """GET / — returns API info."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "docs" in data


@pytest.mark.asyncio
async def test_metrics_endpoint(client: AsyncClient):
    """GET /metrics — returns observability metrics."""
    response = await client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "uptime_seconds" in data
    assert "websocket_connections" in data
    assert data["version"] == "1.0.0"
