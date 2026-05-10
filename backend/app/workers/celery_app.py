from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "analytics_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "evaluate-alerts-every-minute": {
            "task": "app.workers.tasks.evaluate_all_alerts",
            "schedule": 60.0,
        },
        "generate-scheduled-reports": {
            "task": "app.workers.tasks.generate_due_reports",
            "schedule": 300.0,  # Check every 5 minutes
        },
    },
)
