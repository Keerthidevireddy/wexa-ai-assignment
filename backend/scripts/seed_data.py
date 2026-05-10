"""Database seed script — populates development data for testing.

Usage:
    python -m scripts.seed_data

Creates:
  - Demo organization + admin user
  - Sample events (page_view, signup, purchase, error)
  - Sample dashboard with widgets
  - Sample alert rule
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Use SQLite for local seeding if no Postgres available
DATABASE_URL = "sqlite+aiosqlite:///./seed_demo.db"


async def seed():
    from app.db.session import Base
    from app.models.user import Organization, User, UserRole, APIKey
    from app.models.event import Event
    from app.models.dashboard import Dashboard, Widget
    from app.models.alert import Alert, AlertStatus
    from app.models.report import ScheduledReport
    from app.core.security import hash_password

    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        # ─── Organization ────────────────────────────
        org = Organization(name="Acme Analytics", slug="acme-analytics")
        db.add(org)
        await db.flush()
        print(f"✅ Created org: {org.name} (id={org.id})")

        # ─── Admin User ─────────────────────────────
        admin = User(
            email="admin@acme.com",
            hashed_password=hash_password("admin123456"),
            full_name="Admin User",
            role=UserRole.OWNER,
            org_id=org.id,
        )
        db.add(admin)
        await db.flush()
        print(f"✅ Created user: {admin.email} (role={admin.role})")

        # ─── Analyst User ───────────────────────────
        analyst = User(
            email="analyst@acme.com",
            hashed_password=hash_password("analyst123456"),
            full_name="Jane Analyst",
            role=UserRole.ANALYST,
            org_id=org.id,
        )
        db.add(analyst)
        await db.flush()
        print(f"✅ Created user: {analyst.email} (role={analyst.role})")

        # ─── Events (100 sample events) ─────────────
        event_types = [
            ("page_view", "api"),
            ("signup", "api"),
            ("purchase", "api"),
            ("error", "webhook"),
            ("deploy", "webhook"),
            ("session_start", "api"),
        ]
        now = datetime.now(timezone.utc)
        events = []
        for i in range(100):
            name, source = event_types[i % len(event_types)]
            events.append(Event(
                org_id=org.id,
                name=name,
                source=source,
                properties={"page": f"/page-{i % 10}", "browser": "Chrome"},
                user_id=str(uuid.uuid4()),
                session_id=str(uuid.uuid4())[:8],
                created_at=now - timedelta(hours=i),
            ))
        db.add_all(events)
        await db.flush()
        print(f"✅ Created {len(events)} sample events")

        # ─── Dashboard + Widgets ─────────────────────
        dashboard = Dashboard(
            org_id=org.id,
            name="Web Analytics Overview",
            description="Track page views, signups, and errors",
            is_public=True,
            public_slug="demo-analytics",
            refresh_interval=30,
            created_by=admin.id,
        )
        db.add(dashboard)
        await db.flush()

        widgets = [
            Widget(dashboard_id=dashboard.id, title="Page Views", widget_type="line_chart",
                   query_config={"event_name": "page_view", "aggregation": "count"},
                   time_range="7d", position={"x": 0, "y": 0, "w": 6, "h": 4}),
            Widget(dashboard_id=dashboard.id, title="Total Signups", widget_type="kpi_card",
                   query_config={"event_name": "signup", "aggregation": "count"},
                   time_range="7d", position={"x": 6, "y": 0, "w": 3, "h": 2}),
            Widget(dashboard_id=dashboard.id, title="Errors", widget_type="kpi_card",
                   query_config={"event_name": "error", "aggregation": "count"},
                   time_range="24h", position={"x": 9, "y": 0, "w": 3, "h": 2}),
            Widget(dashboard_id=dashboard.id, title="Event Distribution", widget_type="pie_chart",
                   query_config={"aggregation": "count"},
                   time_range="30d", position={"x": 0, "y": 4, "w": 6, "h": 4}),
        ]
        db.add_all(widgets)
        await db.flush()
        print(f"✅ Created dashboard: {dashboard.name} with {len(widgets)} widgets")

        # ─── Alert Rule ──────────────────────────────
        alert = Alert(
            org_id=org.id,
            name="High Error Rate",
            description="Alert when errors exceed 10 in 5 minutes",
            event_name="error",
            metric="count",
            operator=">",
            threshold=10,
            window_minutes=5,
            channels={"in_app": True, "email": True, "webhook_url": ""},
            created_by=admin.id,
        )
        db.add(alert)
        await db.flush()
        print(f"✅ Created alert: {alert.name}")

        # ─── Scheduled Report ────────────────────────
        report = ScheduledReport(
            org_id=org.id,
            dashboard_id=dashboard.id,
            name="Weekly Analytics Report",
            frequency="weekly",
            format="pdf",
            recipients=["admin@acme.com", "team@acme.com"],
            created_by=admin.id,
        )
        db.add(report)
        await db.flush()
        print(f"✅ Created scheduled report: {report.name}")

        await db.commit()
        print("\n🎉 Seed complete! Login with: admin@acme.com / admin123456")


if __name__ == "__main__":
    asyncio.run(seed())
