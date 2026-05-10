from datetime import datetime
from pydantic import BaseModel, Field


class AlertCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    event_name: str
    metric: str = "count"  # count | sum | avg
    operator: str = ">"  # > | < | >= | <= | ==
    threshold: float
    window_minutes: int = Field(default=10, ge=1, le=1440)
    channels: dict = Field(default_factory=lambda: {"in_app": True, "email": False, "webhook": None})


class AlertUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    event_name: str | None = None
    metric: str | None = None
    operator: str | None = None
    threshold: float | None = None
    window_minutes: int | None = None
    status: str | None = None
    channels: dict | None = None


class AlertOut(BaseModel):
    id: str
    org_id: str
    name: str
    description: str | None
    event_name: str
    metric: str
    operator: str
    threshold: float
    window_minutes: int
    status: str
    channels: dict
    created_by: str
    created_at: datetime
    last_triggered_at: datetime | None
    muted_until: datetime | None

    model_config = {"from_attributes": True}


class AlertHistoryOut(BaseModel):
    id: str
    alert_id: str
    status: str
    triggered_value: float | None
    message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationOut(BaseModel):
    id: str
    title: str
    message: str
    is_read: bool
    channel: str
    extra_data: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class MuteAlertRequest(BaseModel):
    minutes: int = Field(default=60, ge=1, le=10080)  # max 1 week
