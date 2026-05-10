"""Service layer for scheduled report management."""

import os
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.report import ScheduledReport, ReportRun, ReportFrequency, ReportStatus
from app.models.dashboard import Dashboard
from app.schemas.report import ReportCreate, ReportUpdate


REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "generated_reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def _next_run(frequency: str, from_time: datetime | None = None) -> datetime:
    """Calculate next run time based on frequency."""
    now = from_time or datetime.now(timezone.utc)
    if frequency == ReportFrequency.DAILY:
        return now + timedelta(days=1)
    elif frequency == ReportFrequency.WEEKLY:
        return now + timedelta(weeks=1)
    elif frequency == ReportFrequency.MONTHLY:
        return now + timedelta(days=30)
    return now + timedelta(weeks=1)


class ReportService:

    @staticmethod
    async def create(db: AsyncSession, org_id: str, user_id: str, data: ReportCreate) -> ScheduledReport:
        """Create a new scheduled report for a dashboard."""
        report = ScheduledReport(
            org_id=org_id,
            dashboard_id=data.dashboard_id,
            name=data.name,
            frequency=data.frequency,
            format=data.format,
            recipients=data.recipients,
            created_by=user_id,
            next_run_at=_next_run(data.frequency),
        )
        db.add(report)
        await db.flush()
        return report

    @staticmethod
    async def list_all(db: AsyncSession, org_id: str) -> list[ScheduledReport]:
        result = await db.execute(
            select(ScheduledReport)
            .where(ScheduledReport.org_id == org_id)
            .order_by(ScheduledReport.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, report_id: str, org_id: str) -> ScheduledReport | None:
        result = await db.execute(
            select(ScheduledReport).where(
                ScheduledReport.id == report_id,
                ScheduledReport.org_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update(db: AsyncSession, report_id: str, org_id: str, data: ReportUpdate) -> ScheduledReport | None:
        report = await ReportService.get_by_id(db, report_id, org_id)
        if not report:
            return None
        for field, val in data.model_dump(exclude_unset=True).items():
            setattr(report, field, val)
        if data.frequency:
            report.next_run_at = _next_run(data.frequency)
        await db.flush()
        return report

    @staticmethod
    async def delete(db: AsyncSession, report_id: str, org_id: str) -> bool:
        report = await ReportService.get_by_id(db, report_id, org_id)
        if not report:
            return False
        await db.delete(report)
        await db.flush()
        return True

    @staticmethod
    async def get_history(db: AsyncSession, report_id: str) -> list[ReportRun]:
        result = await db.execute(
            select(ReportRun)
            .where(ReportRun.report_id == report_id)
            .order_by(ReportRun.started_at.desc())
            .limit(50)
        )
        return list(result.scalars().all())

    @staticmethod
    async def generate_report(db: AsyncSession, report: ScheduledReport) -> ReportRun:
        """Generate a report snapshot (PDF/PNG) for a dashboard.

        In production, this would use a headless browser (Playwright/Puppeteer)
        to screenshot the dashboard. Here we generate a structured HTML report
        and save it as the output file.
        """
        run = ReportRun(
            report_id=report.id,
            status=ReportStatus.GENERATING,
        )
        db.add(run)
        await db.flush()

        try:
            # Get dashboard data
            dash_result = await db.execute(
                select(Dashboard)
                .options(selectinload(Dashboard.widgets))
                .where(Dashboard.id == report.dashboard_id)
            )
            dashboard = dash_result.scalar_one_or_none()

            if not dashboard:
                run.status = ReportStatus.FAILED
                run.error_message = "Dashboard not found"
                run.completed_at = datetime.now(timezone.utc)
                await db.flush()
                return run

            # Generate HTML report (in production: headless browser screenshot)
            html_content = _generate_html_report(dashboard, report)
            filename = f"report_{report.id}_{run.id}.html"
            filepath = os.path.join(REPORTS_DIR, filename)

            with open(filepath, "w") as f:
                f.write(html_content)

            run.status = ReportStatus.COMPLETED
            run.file_path = filepath
            run.file_size_bytes = os.path.getsize(filepath)
            run.completed_at = datetime.now(timezone.utc)

            # Update report metadata
            report.last_sent_at = datetime.now(timezone.utc)
            report.next_run_at = _next_run(report.frequency)

            await db.flush()
            return run

        except Exception as e:
            run.status = ReportStatus.FAILED
            run.error_message = str(e)
            run.completed_at = datetime.now(timezone.utc)
            await db.flush()
            return run


def _generate_html_report(dashboard, report) -> str:
    """Generate an HTML report snapshot of a dashboard."""
    widgets_html = ""
    for w in (dashboard.widgets or []):
        widgets_html += f"""
        <div class="widget">
            <h3>{w.title}</h3>
            <p>Type: {w.widget_type} | Time Range: {w.time_range}</p>
            <p>Query: {w.query_config}</p>
        </div>
        """

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Report: {report.name}</title>
    <style>
        body {{ font-family: Inter, sans-serif; padding: 40px; background: #0f0f14; color: #e0e0e0; }}
        h1 {{ color: #7c5cfc; }}
        .meta {{ color: #888; font-size: 14px; margin-bottom: 24px; }}
        .widget {{ background: #1a1a24; border-radius: 12px; padding: 20px; margin: 16px 0; border: 1px solid #2a2a3a; }}
        .widget h3 {{ color: #e0e0e0; margin: 0 0 8px 0; }}
        .widget p {{ color: #888; margin: 4px 0; font-size: 13px; }}
    </style>
</head>
<body>
    <h1>📊 {report.name}</h1>
    <div class="meta">
        Dashboard: {dashboard.name} | Frequency: {report.frequency} | Generated: {datetime.now(timezone.utc).isoformat()}
    </div>
    {widgets_html}
    <p style="color: #555; margin-top: 40px; font-size: 12px;">Generated by Analytics Platform</p>
</body>
</html>"""
