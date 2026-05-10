from datetime import datetime
from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    properties: dict = Field(default_factory=dict)
    user_id: str | None = None
    session_id: str | None = None
    timestamp: datetime | None = None  # optional, defaults to server time


class BatchEventCreate(BaseModel):
    events: list[EventCreate] = Field(min_length=1, max_length=1000)


class EventOut(BaseModel):
    id: str
    org_id: str
    name: str
    source: str
    properties: dict
    user_id: str | None
    session_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EventQueryParams(BaseModel):
    event_name: str | None = None
    time_range: str = "7d"  # 1h | 24h | 7d | 30d
    aggregation: str = "count"  # count | sum | avg | unique
    group_by: str | None = None
    start: datetime | None = None
    end: datetime | None = None


class AggregationResult(BaseModel):
    labels: list[str]
    values: list[float]
    total: float


class SavedQueryCreate(BaseModel):
    name: str
    event_name: str | None = None
    aggregation: str = "count"
    group_by: str | None = None
    filters: dict = Field(default_factory=dict)
    time_range: str = "7d"


class SavedQueryOut(BaseModel):
    id: str
    name: str
    event_name: str | None
    aggregation: str
    group_by: str | None
    filters: dict
    time_range: str
    created_at: datetime

    model_config = {"from_attributes": True}
