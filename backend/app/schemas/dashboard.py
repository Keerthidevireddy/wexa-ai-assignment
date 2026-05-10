from datetime import datetime
from pydantic import BaseModel, Field


class WidgetCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    widget_type: str  # line_chart | bar_chart | pie_chart | kpi_card | table
    query_config: dict = Field(default_factory=dict)
    time_range: str = "7d"
    position: dict = Field(default_factory=lambda: {"x": 0, "y": 0, "w": 6, "h": 4})
    style_config: dict = Field(default_factory=dict)


class WidgetOut(BaseModel):
    id: str
    dashboard_id: str
    title: str
    widget_type: str
    query_config: dict
    time_range: str
    position: dict
    style_config: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class WidgetUpdate(BaseModel):
    title: str | None = None
    widget_type: str | None = None
    query_config: dict | None = None
    time_range: str | None = None
    position: dict | None = None
    style_config: dict | None = None


class DashboardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    is_public: bool = False
    refresh_interval: int = 0
    widgets: list[WidgetCreate] = Field(default_factory=list)


class DashboardUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_public: bool | None = None
    refresh_interval: int | None = None
    layout: dict | None = None


class DashboardOut(BaseModel):
    id: str
    org_id: str
    name: str
    description: str | None
    is_public: bool
    public_slug: str | None
    refresh_interval: int
    layout: dict
    created_by: str
    created_at: datetime
    updated_at: datetime
    widgets: list[WidgetOut] = []

    model_config = {"from_attributes": True}


class DashboardListOut(BaseModel):
    id: str
    name: str
    description: str | None
    is_public: bool
    widget_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
