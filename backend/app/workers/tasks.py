import asyncio
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.workers.celery_app import celery_app
from app.core.config import settings
from app.models.alert import Alert, AlertStatus
from app.services.alert_service import AlertService

log = structlog.get_logger()

# Separate engine for celery workers (runs outside FastAPI lifecycle)
_engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


def _run_async(coro):
    """Helper to run async code from sync Celery tasks."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="app.workers.tasks.evaluate_all_alerts",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def evaluate_all_alerts(self):
    """Celery Beat task: evaluate all active alerts with retry/backoff."""
    try:
        _run_async(_evaluate_all())
    except Exception as exc:
        log.error("alert_evaluation_failed", error=str(exc), retry=self.request.retries)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))  # exponential backoff


async def _evaluate_all():
    async with _session_factory() as db:
        result = await db.execute(
            select(Alert).where(
                Alert.status.in_([AlertStatus.ACTIVE, AlertStatus.TRIGGERED, AlertStatus.MUTED])
            )
        )
        alerts = result.scalars().all()
        triggered_count = 0
        for alert in alerts:
            try:
                triggered, value = await AlertService.evaluate_alert(db, alert)
                if triggered:
                    triggered_count += 1
            except Exception as e:
                log.error("single_alert_eval_failed", alert_id=alert.id, error=str(e))
                continue
        await db.commit()
        log.info("alerts_evaluated", total=len(alerts), triggered=triggered_count)


@celery_app.task(
    name="app.workers.tasks.process_event_batch",
    bind=True,
    max_retries=5,
    default_retry_delay=10,
    acks_late=True,
    reject_on_worker_lost=True,
)
def process_event_batch(self, org_id: str, events: list[dict]):
    """Async event processing with retry and dead letter handling."""
    try:
        _run_async(_process_batch(org_id, events))
        log.info("batch_processed", org_id=org_id, count=len(events))
    except Exception as exc:
        log.error("batch_processing_failed", org_id=org_id, error=str(exc), retry=self.request.retries)
        if self.request.retries >= self.max_retries:
            # Dead letter: log for manual recovery
            log.critical("batch_dead_lettered", org_id=org_id, count=len(events), events=events[:3])
            return
        raise self.retry(exc=exc, countdown=10 * (2 ** self.request.retries))  # exponential backoff


async def _process_batch(org_id: str, events: list[dict]):
    from app.models.event import Event
    async with _session_factory() as db:
        for e in events:
            event = Event(
                org_id=org_id,
                name=e["name"],
                source="api",
                properties=e.get("properties", {}),
                user_id=e.get("user_id"),
                session_id=e.get("session_id"),
            )
            db.add(event)
        await db.commit()


@celery_app.task(
    name="app.workers.tasks.send_webhook_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def send_webhook_notification(self, webhook_url: str, payload: dict):
    """Send alert notification to a webhook URL with retries."""
    import httpx
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(webhook_url, json=payload)
            response.raise_for_status()
        log.info("webhook_sent", url=webhook_url, status=response.status_code)
    except Exception as exc:
        log.error("webhook_failed", url=webhook_url, error=str(exc), retry=self.request.retries)
        raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))


@celery_app.task(
    name="app.workers.tasks.generate_due_reports",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
)
def generate_due_reports(self):
    """Celery Beat task: generate all scheduled reports that are due."""
    try:
        _run_async(_generate_due())
    except Exception as exc:
        log.error("report_generation_failed", error=str(exc), retry=self.request.retries)
        raise self.retry(exc=exc, countdown=120)


async def _generate_due():
    from datetime import datetime, timezone
    from app.models.report import ScheduledReport
    from app.services.report_service import ReportService

    async with _session_factory() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(ScheduledReport).where(
                ScheduledReport.is_active == True,
                ScheduledReport.next_run_at <= now,
            )
        )
        reports = result.scalars().all()
        generated = 0
        for report in reports:
            try:
                await ReportService.generate_report(db, report)
                generated += 1
            except Exception as e:
                log.error("single_report_failed", report_id=report.id, error=str(e))
                continue
        await db.commit()
        log.info("reports_generated", due=len(reports), generated=generated)
