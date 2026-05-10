import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class WidgetType(str, Enum):
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    KPI_CARD = "kpi_card"
    TABLE = "table"


class Dashboard(Base):
    __tablename__ = "dashboards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    public_slug: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    refresh_interval: Mapped[int] = mapped_column(Integer, default=0)  # 0 = off, seconds
    layout: Mapped[dict] = mapped_column(JSON, default=dict)  # grid layout positions
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    widgets: Mapped[list["Widget"]] = relationship("Widget", back_populates="dashboard", cascade="all, delete-orphan")
    organization = relationship("Organization", back_populates="dashboards")


class Widget(Base):
    __tablename__ = "widgets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dashboard_id: Mapped[str] = mapped_column(String(36), ForeignKey("dashboards.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    widget_type: Mapped[str] = mapped_column(String(20), nullable=False)
    query_config: Mapped[dict] = mapped_column(JSON, default=dict)  # event_name, aggregation, filters, group_by
    time_range: Mapped[str] = mapped_column(String(20), default="7d")
    position: Mapped[dict] = mapped_column(JSON, default=dict)  # {x, y, w, h} for grid layout
    style_config: Mapped[dict] = mapped_column(JSON, default=dict)  # colors, labels, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    dashboard: Mapped["Dashboard"] = relationship("Dashboard", back_populates="widgets")
