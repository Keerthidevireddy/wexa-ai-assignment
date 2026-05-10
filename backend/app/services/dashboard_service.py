import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.dashboard import Dashboard, Widget
from app.schemas.dashboard import DashboardCreate, DashboardUpdate, WidgetCreate, WidgetUpdate


class DashboardService:

    @staticmethod
    async def create(db: AsyncSession, org_id: str, user_id: str, data: DashboardCreate) -> Dashboard:
        public_slug = None
        if data.is_public:
            public_slug = f"{data.name.lower().replace(' ', '-')[:30]}-{str(uuid.uuid4())[:8]}"

        dashboard = Dashboard(
            org_id=org_id,
            name=data.name,
            description=data.description,
            is_public=data.is_public,
            public_slug=public_slug,
            refresh_interval=data.refresh_interval,
            created_by=user_id,
        )
        db.add(dashboard)
        await db.flush()

        for w in data.widgets:
            widget = Widget(
                dashboard_id=dashboard.id,
                title=w.title,
                widget_type=w.widget_type,
                query_config=w.query_config,
                time_range=w.time_range,
                position=w.position,
                style_config=w.style_config,
            )
            db.add(widget)
        await db.flush()

        return await DashboardService.get_by_id(db, dashboard.id, org_id)

    @staticmethod
    async def list_all(db: AsyncSession, org_id: str):
        result = await db.execute(
            select(Dashboard)
            .options(selectinload(Dashboard.widgets))
            .where(Dashboard.org_id == org_id)
            .order_by(Dashboard.updated_at.desc())
        )
        dashboards = result.scalars().all()
        return dashboards

    @staticmethod
    async def get_by_id(db: AsyncSession, dashboard_id: str, org_id: str) -> Dashboard | None:
        result = await db.execute(
            select(Dashboard)
            .options(selectinload(Dashboard.widgets))
            .where(Dashboard.id == dashboard_id, Dashboard.org_id == org_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_public(db: AsyncSession, slug: str) -> Dashboard | None:
        result = await db.execute(
            select(Dashboard)
            .options(selectinload(Dashboard.widgets))
            .where(Dashboard.public_slug == slug, Dashboard.is_public == True)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update(db: AsyncSession, dashboard_id: str, org_id: str, data: DashboardUpdate) -> Dashboard | None:
        dashboard = await DashboardService.get_by_id(db, dashboard_id, org_id)
        if not dashboard:
            return None

        for field, val in data.model_dump(exclude_unset=True).items():
            setattr(dashboard, field, val)

        if data.is_public and not dashboard.public_slug:
            dashboard.public_slug = f"{dashboard.name.lower().replace(' ', '-')[:30]}-{str(uuid.uuid4())[:8]}"
        elif data.is_public is False:
            dashboard.public_slug = None

        dashboard.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return dashboard

    @staticmethod
    async def delete(db: AsyncSession, dashboard_id: str, org_id: str) -> bool:
        dashboard = await DashboardService.get_by_id(db, dashboard_id, org_id)
        if not dashboard:
            return False
        await db.delete(dashboard)
        await db.flush()
        return True

    # ─── Widget ops ──────────────────────────────
    @staticmethod
    async def add_widget(db: AsyncSession, dashboard_id: str, org_id: str, data: WidgetCreate) -> Widget | None:
        dashboard = await DashboardService.get_by_id(db, dashboard_id, org_id)
        if not dashboard:
            return None

        widget = Widget(
            dashboard_id=dashboard_id,
            title=data.title,
            widget_type=data.widget_type,
            query_config=data.query_config,
            time_range=data.time_range,
            position=data.position,
            style_config=data.style_config,
        )
        db.add(widget)
        await db.flush()
        return widget

    @staticmethod
    async def update_widget(db: AsyncSession, widget_id: str, data: WidgetUpdate) -> Widget | None:
        result = await db.execute(select(Widget).where(Widget.id == widget_id))
        widget = result.scalar_one_or_none()
        if not widget:
            return None
        for field, val in data.model_dump(exclude_unset=True).items():
            setattr(widget, field, val)
        await db.flush()
        return widget

    @staticmethod
    async def delete_widget(db: AsyncSession, widget_id: str) -> bool:
        result = await db.execute(select(Widget).where(Widget.id == widget_id))
        widget = result.scalar_one_or_none()
        if not widget:
            return False
        await db.delete(widget)
        await db.flush()
        return True
