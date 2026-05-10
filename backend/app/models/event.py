import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Event(Base):
    """Time-series event table. Partitioned by created_at in production."""

    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_org_created", "org_id", "created_at"),
        Index("ix_events_name", "name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="api")  # api | csv | webhook
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    organization = relationship("Organization")


class SavedQuery(Base):
    __tablename__ = "saved_queries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aggregation: Mapped[str] = mapped_column(String(50), default="count")  # count | sum | avg | unique
    group_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    time_range: Mapped[str] = mapped_column(String(20), default="7d")  # 1h | 24h | 7d | 30d | custom
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
