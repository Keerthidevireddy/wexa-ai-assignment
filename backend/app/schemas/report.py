"""Pydantic schemas for scheduled reports."""

from datetime import datetime
from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    """Create a new scheduled report."""
    dashboard_id: str
    name: str = Field(..., min_length=1, max_length=255)
    frequency: str = "weekly"  # daily | weekly | monthly
    format: str = "pdf"  # pdf | png
    recipients: list[str] = Field(default_factory=list)  # email addresses


class ReportUpdate(BaseModel):
    """Update a scheduled report."""
    name: str | None = None
    frequency: str | None = None
    format: str | None = None
    recipients: list[str] | None = None
    is_active: bool | None = None


class ReportOut(BaseModel):
    """Scheduled report response."""
    id: str
    org_id: str
    dashboard_id: str
    name: str
    frequency: str
    format: str
    recipients: list
    is_active: bool
    created_by: str
    created_at: datetime
    last_sent_at: datetime | None
    next_run_at: datetime | None

    model_config = {"from_attributes": True}


class ReportRunOut(BaseModel):
    """Report execution history entry."""
    id: str
    report_id: str
    status: str
    file_path: str | None
    file_size_bytes: int | None
    error_message: str | None
    recipients_sent: list
    started_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}
