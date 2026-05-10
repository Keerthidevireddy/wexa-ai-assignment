"""Tests for all scheduled report endpoints.

Endpoints tested:
  POST   /reports/                  Create a scheduled report
  GET    /reports/                  List reports
  GET    /reports/{id}              Get report detail
  PATCH  /reports/{id}              Update report
  DELETE /reports/{id}              Delete report
  POST   /reports/{id}/run          Manually trigger report generation
  GET    /reports/{id}/history      Get report execution history
"""

import pytest
from httpx import AsyncClient
from tests.conftest import create_test_user


# ════════════════════════════════════════════════
#  Helper: create a dashboard first, then a report
# ════════════════════════════════════════════════

async def _create_dashboard(client: AsyncClient, headers: dict) -> str:
    """Helper to create a dashboard and return its ID."""
    resp = await client.post("/api/v1/dashboards/", json={
        "name": "Report Test Dashboard",
        "widgets": [{"title": "KPI", "widget_type": "kpi_card", "query_config": {"event_name": "test"}}],
    }, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


# ════════════════════════════════════════════════
#  CREATE REPORT
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_report(client: AsyncClient):
    """POST /reports/ — create scheduled report."""
    user = await create_test_user(client, "report_create@test.com")
    dash_id = await _create_dashboard(client, user["headers"])

    response = await client.post("/api/v1/reports/", json={
        "dashboard_id": dash_id,
        "name": "Weekly Sales Report",
        "frequency": "weekly",
        "format": "pdf",
        "recipients": ["boss@example.com", "team@example.com"],
    }, headers=user["headers"])
    assert response.status_code == 201, f"Got {response.status_code}: {response.text}"
    data = response.json()
    assert data["name"] == "Weekly Sales Report"
    assert data["frequency"] == "weekly"
    assert data["format"] == "pdf"
    assert len(data["recipients"]) == 2
    assert data["is_active"] is True
    assert data["next_run_at"] is not None


# ════════════════════════════════════════════════
#  LIST REPORTS
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_reports(client: AsyncClient):
    """GET /reports/ — list org reports."""
    user = await create_test_user(client, "report_list@test.com")
    dash_id = await _create_dashboard(client, user["headers"])

    await client.post("/api/v1/reports/", json={
        "dashboard_id": dash_id, "name": "R1", "frequency": "daily",
    }, headers=user["headers"])
    await client.post("/api/v1/reports/", json={
        "dashboard_id": dash_id, "name": "R2", "frequency": "monthly",
    }, headers=user["headers"])

    response = await client.get("/api/v1/reports/", headers=user["headers"])
    assert response.status_code == 200
    assert len(response.json()) >= 2


# ════════════════════════════════════════════════
#  GET REPORT DETAIL
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_report_detail(client: AsyncClient):
    """GET /reports/{id} — get report by ID."""
    user = await create_test_user(client, "report_detail@test.com")
    dash_id = await _create_dashboard(client, user["headers"])

    create = await client.post("/api/v1/reports/", json={
        "dashboard_id": dash_id, "name": "Detail Report",
    }, headers=user["headers"])
    report_id = create.json()["id"]

    response = await client.get(f"/api/v1/reports/{report_id}", headers=user["headers"])
    assert response.status_code == 200
    assert response.json()["name"] == "Detail Report"


@pytest.mark.asyncio
async def test_get_report_not_found(client: AsyncClient):
    """GET /reports/{id} — non-existent returns 404."""
    user = await create_test_user(client, "report_404@test.com")
    response = await client.get("/api/v1/reports/fake-id", headers=user["headers"])
    assert response.status_code == 404


# ════════════════════════════════════════════════
#  UPDATE REPORT
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_update_report(client: AsyncClient):
    """PATCH /reports/{id} — update name and frequency."""
    user = await create_test_user(client, "report_update@test.com")
    dash_id = await _create_dashboard(client, user["headers"])

    create = await client.post("/api/v1/reports/", json={
        "dashboard_id": dash_id, "name": "Old Report",
    }, headers=user["headers"])
    report_id = create.json()["id"]

    response = await client.patch(f"/api/v1/reports/{report_id}", json={
        "name": "Updated Report",
        "frequency": "daily",
    }, headers=user["headers"])
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Report"
    assert response.json()["frequency"] == "daily"


# ════════════════════════════════════════════════
#  DELETE REPORT
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_delete_report(client: AsyncClient):
    """DELETE /reports/{id} — returns 204."""
    user = await create_test_user(client, "report_delete@test.com")
    dash_id = await _create_dashboard(client, user["headers"])

    create = await client.post("/api/v1/reports/", json={
        "dashboard_id": dash_id, "name": "Temp Report",
    }, headers=user["headers"])
    report_id = create.json()["id"]

    response = await client.delete(f"/api/v1/reports/{report_id}", headers=user["headers"])
    assert response.status_code == 204

    # Verify deleted
    get_resp = await client.get(f"/api/v1/reports/{report_id}", headers=user["headers"])
    assert get_resp.status_code == 404


# ════════════════════════════════════════════════
#  MANUAL TRIGGER / GENERATE
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_trigger_report(client: AsyncClient):
    """POST /reports/{id}/run — manually trigger report generation."""
    user = await create_test_user(client, "report_trigger@test.com")
    dash_id = await _create_dashboard(client, user["headers"])

    create = await client.post("/api/v1/reports/", json={
        "dashboard_id": dash_id, "name": "Trigger Report",
    }, headers=user["headers"])
    report_id = create.json()["id"]

    response = await client.post(f"/api/v1/reports/{report_id}/run", headers=user["headers"])
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "completed"
    assert data["file_path"] is not None
    assert data["file_size_bytes"] > 0


# ════════════════════════════════════════════════
#  REPORT HISTORY
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_report_history(client: AsyncClient):
    """GET /reports/{id}/history — get execution history."""
    user = await create_test_user(client, "report_history@test.com")
    dash_id = await _create_dashboard(client, user["headers"])

    create = await client.post("/api/v1/reports/", json={
        "dashboard_id": dash_id, "name": "History Report",
    }, headers=user["headers"])
    report_id = create.json()["id"]

    # Trigger once
    await client.post(f"/api/v1/reports/{report_id}/run", headers=user["headers"])

    response = await client.get(f"/api/v1/reports/{report_id}/history", headers=user["headers"])
    assert response.status_code == 200
    history = response.json()
    assert len(history) >= 1
    assert history[0]["status"] == "completed"
