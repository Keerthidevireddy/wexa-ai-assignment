from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_analyst
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import (
    DashboardCreate, DashboardUpdate, DashboardOut,
    WidgetCreate, WidgetUpdate, WidgetOut,
)
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboards", tags=["Dashboards"])

# ─── Dashboard Templates ─────────────────────────
DASHBOARD_TEMPLATES = {
    "web_analytics": {
        "name": "Web Analytics",
        "description": "Track page views, sessions, and user behavior across your website.",
        "widgets": [
            {"title": "Page Views", "widget_type": "line_chart", "query_config": {"event_name": "page_view", "aggregation": "count"}, "time_range": "7d", "position": {"x": 0, "y": 0, "w": 6, "h": 4}},
            {"title": "Unique Visitors", "widget_type": "kpi_card", "query_config": {"event_name": "page_view", "aggregation": "unique"}, "time_range": "7d", "position": {"x": 6, "y": 0, "w": 3, "h": 2}},
            {"title": "Total Sessions", "widget_type": "kpi_card", "query_config": {"event_name": "session_start", "aggregation": "count"}, "time_range": "7d", "position": {"x": 9, "y": 0, "w": 3, "h": 2}},
            {"title": "Top Events", "widget_type": "bar_chart", "query_config": {"aggregation": "count"}, "time_range": "7d", "position": {"x": 6, "y": 2, "w": 6, "h": 4}},
            {"title": "Traffic Sources", "widget_type": "pie_chart", "query_config": {"event_name": "page_view", "aggregation": "count", "group_by": "source"}, "time_range": "30d", "position": {"x": 0, "y": 4, "w": 6, "h": 4}},
        ],
    },
    "sales": {
        "name": "Sales Dashboard",
        "description": "Monitor revenue, conversions, and sales pipeline metrics.",
        "widgets": [
            {"title": "Revenue", "widget_type": "kpi_card", "query_config": {"event_name": "purchase", "aggregation": "sum"}, "time_range": "30d", "position": {"x": 0, "y": 0, "w": 4, "h": 2}},
            {"title": "Conversions", "widget_type": "kpi_card", "query_config": {"event_name": "purchase", "aggregation": "count"}, "time_range": "30d", "position": {"x": 4, "y": 0, "w": 4, "h": 2}},
            {"title": "Avg Order Value", "widget_type": "kpi_card", "query_config": {"event_name": "purchase", "aggregation": "avg"}, "time_range": "30d", "position": {"x": 8, "y": 0, "w": 4, "h": 2}},
            {"title": "Revenue Trend", "widget_type": "line_chart", "query_config": {"event_name": "purchase", "aggregation": "sum"}, "time_range": "30d", "position": {"x": 0, "y": 2, "w": 8, "h": 4}},
            {"title": "Sales by Channel", "widget_type": "pie_chart", "query_config": {"event_name": "purchase", "aggregation": "count", "group_by": "channel"}, "time_range": "30d", "position": {"x": 8, "y": 2, "w": 4, "h": 4}},
            {"title": "Recent Transactions", "widget_type": "table", "query_config": {"event_name": "purchase"}, "time_range": "7d", "position": {"x": 0, "y": 6, "w": 12, "h": 4}},
        ],
    },
    "devops": {
        "name": "DevOps Monitor",
        "description": "Track errors, deployments, and system health in real time.",
        "widgets": [
            {"title": "Error Rate", "widget_type": "line_chart", "query_config": {"event_name": "error", "aggregation": "count"}, "time_range": "24h", "position": {"x": 0, "y": 0, "w": 6, "h": 4}},
            {"title": "Errors (24h)", "widget_type": "kpi_card", "query_config": {"event_name": "error", "aggregation": "count"}, "time_range": "24h", "position": {"x": 6, "y": 0, "w": 3, "h": 2}},
            {"title": "Deployments", "widget_type": "kpi_card", "query_config": {"event_name": "deploy", "aggregation": "count"}, "time_range": "7d", "position": {"x": 9, "y": 0, "w": 3, "h": 2}},
            {"title": "Deploys Timeline", "widget_type": "bar_chart", "query_config": {"event_name": "deploy", "aggregation": "count"}, "time_range": "7d", "position": {"x": 6, "y": 2, "w": 6, "h": 4}},
            {"title": "Error Types", "widget_type": "pie_chart", "query_config": {"event_name": "error", "aggregation": "count", "group_by": "type"}, "time_range": "24h", "position": {"x": 0, "y": 4, "w": 6, "h": 4}},
        ],
    },
}


@router.get("/templates")
async def list_templates():
    """List available dashboard templates (Web Analytics, Sales, DevOps)."""
    return [
        {"id": k, "name": v["name"], "description": v["description"], "widget_count": len(v["widgets"])}
        for k, v in DASHBOARD_TEMPLATES.items()
    ]


@router.post("/from-template/{template_id}", response_model=DashboardOut, status_code=status.HTTP_201_CREATED)
async def create_from_template(
    template_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """Create a dashboard from a pre-built template."""
    template = DASHBOARD_TEMPLATES.get(template_id)
    if not template:
        raise NotFoundError(resource="Template", resource_id=template_id)

    data = DashboardCreate(
        name=template["name"],
        description=template["description"],
        widgets=[WidgetCreate(**w) for w in template["widgets"]],
    )
    dashboard = await DashboardService.create(db, current_user.org_id, current_user.id, data)
    return DashboardOut.model_validate(dashboard)


@router.post("/", response_model=DashboardOut, status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    data: DashboardCreate,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """Create a new dashboard with optional inline widgets."""
    dashboard = await DashboardService.create(db, current_user.org_id, current_user.id, data)
    return DashboardOut.model_validate(dashboard)


@router.get("/", response_model=list[DashboardOut])
async def list_dashboards(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all dashboards for the current organization."""
    dashboards = await DashboardService.list_all(db, current_user.org_id)
    return [DashboardOut.model_validate(d) for d in dashboards]


@router.get("/public/{slug}", response_model=DashboardOut)
async def get_public_dashboard(slug: str, db: AsyncSession = Depends(get_db)):
    """Get a public dashboard by its slug (no auth required)."""
    dashboard = await DashboardService.get_public(db, slug)
    if not dashboard:
        raise NotFoundError(resource="Dashboard", resource_id=slug)
    return DashboardOut.model_validate(dashboard)


@router.get("/{dashboard_id}", response_model=DashboardOut)
async def get_dashboard(
    dashboard_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single dashboard by ID with all widgets."""
    dashboard = await DashboardService.get_by_id(db, dashboard_id, current_user.org_id)
    if not dashboard:
        raise NotFoundError(resource="Dashboard", resource_id=dashboard_id)
    return DashboardOut.model_validate(dashboard)


@router.patch("/{dashboard_id}", response_model=DashboardOut)
async def update_dashboard(
    dashboard_id: str,
    data: DashboardUpdate,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """Update dashboard name, description, visibility, or layout."""
    dashboard = await DashboardService.update(db, dashboard_id, current_user.org_id, data)
    if not dashboard:
        raise NotFoundError(resource="Dashboard", resource_id=dashboard_id)
    return DashboardOut.model_validate(dashboard)


@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(
    dashboard_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """Delete a dashboard and all its widgets."""
    success = await DashboardService.delete(db, dashboard_id, current_user.org_id)
    if not success:
        raise NotFoundError(resource="Dashboard", resource_id=dashboard_id)


# ─── Widgets ─────────────────────────────────────
@router.post("/{dashboard_id}/widgets", response_model=WidgetOut, status_code=status.HTTP_201_CREATED)
async def add_widget(
    dashboard_id: str,
    data: WidgetCreate,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """Add a new widget to a dashboard."""
    widget = await DashboardService.add_widget(db, dashboard_id, current_user.org_id, data)
    if not widget:
        raise NotFoundError(resource="Dashboard", resource_id=dashboard_id)
    return WidgetOut.model_validate(widget)


@router.patch("/widgets/{widget_id}", response_model=WidgetOut)
async def update_widget(
    widget_id: str,
    data: WidgetUpdate,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """Update widget configuration, position, or style."""
    widget = await DashboardService.update_widget(db, widget_id, data)
    if not widget:
        raise NotFoundError(resource="Widget", resource_id=widget_id)
    return WidgetOut.model_validate(widget)


@router.delete("/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_widget(
    widget_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """Remove a widget from its dashboard."""
    success = await DashboardService.delete_widget(db, widget_id)
    if not success:
        raise NotFoundError(resource="Widget", resource_id=widget_id)
