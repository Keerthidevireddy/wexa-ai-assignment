"""Database seed script — populate with demo data for testing."""

import asyncio
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User, Organization, UserRole
from app.models.event import Event
from app.models.dashboard import Dashboard, Widget
from app.models.alert import Alert, AlertStatus
from app.db.session import Base


async def seed():
    engine = create_async_engine(settings.DATABASE_URL)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        # ─── Organization ────────────────────────
        org = Organization(name="Demo Corp", slug="demo-corp")
        db.add(org)
        await db.flush()

        # ─── Users ───────────────────────────────
        owner = User(
            email="admin@demo.com",
            hashed_password=hash_password("password123"),
            full_name="Admin User",
            role=UserRole.OWNER,
            org_id=org.id,
        )
        analyst = User(
            email="analyst@demo.com",
            hashed_password=hash_password("password123"),
            full_name="Data Analyst",
            role=UserRole.ANALYST,
            org_id=org.id,
        )
        viewer = User(
            email="viewer@demo.com",
            hashed_password=hash_password("password123"),
            full_name="Viewer User",
            role=UserRole.VIEWER,
            org_id=org.id,
        )
        db.add_all([owner, analyst, viewer])
        await db.flush()

        # ─── Events (last 30 days) ──────────────
        event_types = ["page_view", "button_click", "signup", "purchase", "error", "api_call"]
        now = datetime.now(timezone.utc)
        events = []
        for day in range(30):
            dt = now - timedelta(days=day)
            daily_count = random.randint(50, 200)
            for _ in range(daily_count):
                event_name = random.choice(event_types)
                events.append(Event(
                    org_id=org.id,
                    name=event_name,
                    source=random.choice(["api", "csv", "webhook"]),
                    properties={
                        "page": random.choice(["/home", "/pricing", "/docs", "/blog", "/dashboard"]),
                        "browser": random.choice(["chrome", "firefox", "safari", "edge"]),
                        "country": random.choice(["US", "UK", "DE", "IN", "BR"]),
                        "value": round(random.uniform(1, 500), 2) if event_name == "purchase" else None,
                    },
                    user_id=f"user_{random.randint(1, 50)}",
                    session_id=f"sess_{random.randint(1, 200)}",
                    created_at=dt + timedelta(
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59),
                    ),
                ))
        db.add_all(events)
        await db.flush()
        print(f"✓ Seeded {len(events)} events")

        # ─── Dashboard ──────────────────────────
        dashboard = Dashboard(
            org_id=org.id,
            name="Web Analytics Overview",
            description="Real-time overview of website traffic and conversions",
            is_public=True,
            public_slug="web-analytics-demo",
            refresh_interval=30,
            created_by=owner.id,
        )
        db.add(dashboard)
        await db.flush()

        widgets = [
            Widget(
                dashboard_id=dashboard.id,
                title="Total Page Views",
                widget_type="kpi_card",
                query_config={"event_name": "page_view", "aggregation": "count"},
                time_range="7d",
                position={"x": 0, "y": 0, "w": 3, "h": 3},
            ),
            Widget(
                dashboard_id=dashboard.id,
                title="Signups",
                widget_type="kpi_card",
                query_config={"event_name": "signup", "aggregation": "count"},
                time_range="7d",
                position={"x": 3, "y": 0, "w": 3, "h": 3},
            ),
            Widget(
                dashboard_id=dashboard.id,
                title="Purchases",
                widget_type="kpi_card",
                query_config={"event_name": "purchase", "aggregation": "count"},
                time_range="7d",
                position={"x": 6, "y": 0, "w": 3, "h": 3},
            ),
            Widget(
                dashboard_id=dashboard.id,
                title="Errors",
                widget_type="kpi_card",
                query_config={"event_name": "error", "aggregation": "count"},
                time_range="7d",
                position={"x": 9, "y": 0, "w": 3, "h": 3},
            ),
            Widget(
                dashboard_id=dashboard.id,
                title="Traffic Over Time",
                widget_type="line_chart",
                query_config={"event_name": "page_view", "aggregation": "count"},
                time_range="30d",
                position={"x": 0, "y": 3, "w": 8, "h": 4},
            ),
            Widget(
                dashboard_id=dashboard.id,
                title="Events by Type",
                widget_type="bar_chart",
                query_config={"aggregation": "count"},
                time_range="7d",
                position={"x": 8, "y": 3, "w": 4, "h": 4},
            ),
        ]
        db.add_all(widgets)

        # ─── Alerts ─────────────────────────────
        alert1 = Alert(
            org_id=org.id,
            name="High Error Rate",
            description="Triggers when error count exceeds 50 in 10 minutes",
            event_name="error",
            metric="count",
            operator=">",
            threshold=50,
            window_minutes=10,
            channels={"in_app": True, "email": True, "webhook": None},
            created_by=owner.id,
        )
        alert2 = Alert(
            org_id=org.id,
            name="Low Signups",
            description="Triggers when daily signups drop below 5",
            event_name="signup",
            metric="count",
            operator="<",
            threshold=5,
            window_minutes=1440,
            channels={"in_app": True, "email": False, "webhook": None},
            created_by=owner.id,
        )
        db.add_all([alert1, alert2])

        await db.commit()

    print("✓ Database seeded successfully!")
    print("  Demo login: admin@demo.com / password123")
    print("  Analyst login: analyst@demo.com / password123")
    print("  Viewer login: viewer@demo.com / password123")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
