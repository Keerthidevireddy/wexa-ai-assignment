"""Tests for all dashboard & widget endpoints.

Endpoints tested:
  POST   /dashboards/              - Create dashboard
  GET    /dashboards/              - List dashboards
  GET    /dashboards/public/{slug} - Public dashboard (no auth)
  GET    /dashboards/{id}          - Get dashboard detail
  PATCH  /dashboards/{id}          - Update dashboard
  DELETE /dashboards/{id}          - Delete dashboard
  POST   /dashboards/{id}/widgets  - Add widget
  PATCH  /dashboards/widgets/{id}  - Update widget
  DELETE /dashboards/widgets/{id}  - Delete widget
"""

import pytest
from httpx import AsyncClient
from tests.conftest import create_test_user


# ════════════════════════════════════════════════
#  CREATE DASHBOARD
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_dashboard(client: AsyncClient):
    """POST /dashboards/ — create with name returns 201."""
    user = await create_test_user(client, "dash_create@test.com")
    response = await client.post("/api/v1/dashboards/", json={
        "name": "Sales Dashboard",
        "description": "Monthly sales overview",
        "is_public": False,
    }, headers=user["headers"])
    assert response.status_code == 201, f"Got {response.status_code}: {response.text}"
    data = response.json()
    assert data["name"] == "Sales Dashboard"
    assert data["is_public"] is False
    assert data["org_id"] == user["user"]["org_id"]


@pytest.mark.asyncio
async def test_create_dashboard_with_widgets(client: AsyncClient):
    """POST /dashboards/ — create with inline widgets."""
    user = await create_test_user(client, "dash_widgets@test.com")
    response = await client.post("/api/v1/dashboards/", json={
        "name": "Full Dashboard",
        "widgets": [
            {"title": "KPI", "widget_type": "kpi_card", "query_config": {"event_name": "signup"}},
            {"title": "Chart", "widget_type": "line_chart", "query_config": {"event_name": "page_view"}},
        ],
    }, headers=user["headers"])
    assert response.status_code == 201
    data = response.json()
    assert len(data["widgets"]) == 2


@pytest.mark.asyncio
async def test_create_public_dashboard(client: AsyncClient):
    """POST /dashboards/ — public dashboard gets a slug."""
    user = await create_test_user(client, "dash_public@test.com")
    response = await client.post("/api/v1/dashboards/", json={
        "name": "Public Dash",
        "is_public": True,
    }, headers=user["headers"])
    assert response.status_code == 201
    data = response.json()
    assert data["is_public"] is True
    assert data["public_slug"] is not None


# ════════════════════════════════════════════════
#  LIST DASHBOARDS
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_dashboards(client: AsyncClient):
    """GET /dashboards/ — list returns org dashboards."""
    user = await create_test_user(client, "dash_list@test.com")
    await client.post("/api/v1/dashboards/", json={"name": "D1"}, headers=user["headers"])
    await client.post("/api/v1/dashboards/", json={"name": "D2"}, headers=user["headers"])

    response = await client.get("/api/v1/dashboards/", headers=user["headers"])
    assert response.status_code == 200
    dashboards = response.json()
    assert len(dashboards) >= 2


# ════════════════════════════════════════════════
#  GET DASHBOARD DETAIL
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_dashboard_detail(client: AsyncClient):
    """GET /dashboards/{id} — returns full dashboard with widgets."""
    user = await create_test_user(client, "dash_detail@test.com")
    create = await client.post("/api/v1/dashboards/", json={
        "name": "Detail Test",
    }, headers=user["headers"])
    dash_id = create.json()["id"]

    response = await client.get(f"/api/v1/dashboards/{dash_id}", headers=user["headers"])
    assert response.status_code == 200
    assert response.json()["name"] == "Detail Test"
    assert "widgets" in response.json()


@pytest.mark.asyncio
async def test_get_dashboard_not_found(client: AsyncClient):
    """GET /dashboards/{id} — non-existent ID returns 404."""
    user = await create_test_user(client, "dash_404@test.com")
    response = await client.get("/api/v1/dashboards/fake-uuid", headers=user["headers"])
    assert response.status_code == 404


# ════════════════════════════════════════════════
#  PUBLIC DASHBOARD
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_public_dashboard(client: AsyncClient):
    """GET /dashboards/public/{slug} — works without auth."""
    user = await create_test_user(client, "dash_pub_get@test.com")
    create = await client.post("/api/v1/dashboards/", json={
        "name": "My Public Dash",
        "is_public": True,
    }, headers=user["headers"])
    slug = create.json()["public_slug"]

    # Access WITHOUT auth
    response = await client.get(f"/api/v1/dashboards/public/{slug}")
    assert response.status_code == 200
    assert response.json()["name"] == "My Public Dash"


# ════════════════════════════════════════════════
#  UPDATE DASHBOARD
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_update_dashboard(client: AsyncClient):
    """PATCH /dashboards/{id} — update name and description."""
    user = await create_test_user(client, "dash_update@test.com")
    create = await client.post("/api/v1/dashboards/", json={"name": "Old Name"}, headers=user["headers"])
    dash_id = create.json()["id"]

    response = await client.patch(f"/api/v1/dashboards/{dash_id}", json={
        "name": "New Name",
        "description": "Updated description",
    }, headers=user["headers"])
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["description"] == "Updated description"


# ════════════════════════════════════════════════
#  DELETE DASHBOARD
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_delete_dashboard(client: AsyncClient):
    """DELETE /dashboards/{id} — returns 204."""
    user = await create_test_user(client, "dash_del@test.com")
    create = await client.post("/api/v1/dashboards/", json={"name": "Temp"}, headers=user["headers"])
    dash_id = create.json()["id"]

    response = await client.delete(f"/api/v1/dashboards/{dash_id}", headers=user["headers"])
    assert response.status_code == 204

    # Verify deleted
    get_resp = await client.get(f"/api/v1/dashboards/{dash_id}", headers=user["headers"])
    assert get_resp.status_code == 404


# ════════════════════════════════════════════════
#  ORG ISOLATION
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_dashboard_org_isolation(client: AsyncClient):
    """Dashboards from one org are NOT visible to another org."""
    user1 = await create_test_user(client, "org_iso1@test.com")
    user2 = await create_test_user(client, "org_iso2@test.com")

    await client.post("/api/v1/dashboards/", json={"name": "Org1 Secret"}, headers=user1["headers"])

    response = await client.get("/api/v1/dashboards/", headers=user2["headers"])
    names = [d["name"] for d in response.json()]
    assert "Org1 Secret" not in names


# ════════════════════════════════════════════════
#  WIDGETS
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_add_widget(client: AsyncClient):
    """POST /dashboards/{id}/widgets — add widget to dashboard."""
    user = await create_test_user(client, "widget_add@test.com")
    dash = await client.post("/api/v1/dashboards/", json={"name": "Widget Dash"}, headers=user["headers"])
    dash_id = dash.json()["id"]

    response = await client.post(f"/api/v1/dashboards/{dash_id}/widgets", json={
        "title": "Revenue KPI",
        "widget_type": "kpi_card",
        "query_config": {"event_name": "purchase", "aggregation": "sum"},
    }, headers=user["headers"])
    assert response.status_code == 201
    assert response.json()["title"] == "Revenue KPI"
    assert response.json()["dashboard_id"] == dash_id


@pytest.mark.asyncio
async def test_update_widget(client: AsyncClient):
    """PATCH /dashboards/widgets/{id} — update widget title."""
    user = await create_test_user(client, "widget_upd@test.com")
    dash = await client.post("/api/v1/dashboards/", json={"name": "WD"}, headers=user["headers"])
    dash_id = dash.json()["id"]
    widget = await client.post(f"/api/v1/dashboards/{dash_id}/widgets", json={
        "title": "Old Title", "widget_type": "line_chart",
    }, headers=user["headers"])
    widget_id = widget.json()["id"]

    response = await client.patch(f"/api/v1/dashboards/widgets/{widget_id}", json={
        "title": "New Title",
    }, headers=user["headers"])
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"


@pytest.mark.asyncio
async def test_delete_widget(client: AsyncClient):
    """DELETE /dashboards/widgets/{id} — returns 204."""
    user = await create_test_user(client, "widget_del@test.com")
    dash = await client.post("/api/v1/dashboards/", json={"name": "WD2"}, headers=user["headers"])
    dash_id = dash.json()["id"]
    widget = await client.post(f"/api/v1/dashboards/{dash_id}/widgets", json={
        "title": "Temp Widget", "widget_type": "bar_chart",
    }, headers=user["headers"])
    widget_id = widget.json()["id"]

    response = await client.delete(f"/api/v1/dashboards/widgets/{widget_id}", headers=user["headers"])
    assert response.status_code == 204


# ════════════════════════════════════════════════
#  DASHBOARD TEMPLATES
# ════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_templates(client: AsyncClient):
    """GET /dashboards/templates — returns available templates."""
    response = await client.get("/api/v1/dashboards/templates")
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) == 3
    ids = [t["id"] for t in templates]
    assert "web_analytics" in ids
    assert "sales" in ids
    assert "devops" in ids


@pytest.mark.asyncio
async def test_create_from_template(client: AsyncClient):
    """POST /dashboards/from-template/{id} — creates dashboard with pre-built widgets."""
    user = await create_test_user(client, "tmpl_create@test.com")
    response = await client.post("/api/v1/dashboards/from-template/web_analytics", headers=user["headers"])
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Web Analytics"
    assert len(data["widgets"]) == 5


@pytest.mark.asyncio
async def test_create_from_invalid_template(client: AsyncClient):
    """POST /dashboards/from-template/{id} — invalid template returns 404."""
    user = await create_test_user(client, "tmpl_bad@test.com")
    response = await client.post("/api/v1/dashboards/from-template/nonexistent", headers=user["headers"])
    assert response.status_code == 404
