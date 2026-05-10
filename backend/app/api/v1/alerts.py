from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_analyst
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.user import User
from app.schemas.alert import (
    AlertCreate, AlertUpdate, AlertOut, AlertHistoryOut,
    NotificationOut, MuteAlertRequest,
)
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["Alerts & Notifications"])


@router.post("/", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
async def create_alert(
    data: AlertCreate,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """Create a new threshold-based alert rule."""
    alert = await AlertService.create(db, current_user.org_id, current_user.id, data)
    return AlertOut.model_validate(alert)


@router.get("/", response_model=list[AlertOut])
async def list_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all alert rules for the current organization."""
    alerts = await AlertService.list_all(db, current_user.org_id)
    return [AlertOut.model_validate(a) for a in alerts]


# ─── Notifications (placed BEFORE /{alert_id} to avoid path conflict) ──
@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(
    unread_only: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List notifications for the current user."""
    notifs = await AlertService.get_notifications(db, current_user.id, unread_only)
    return [NotificationOut.model_validate(n) for n in notifs]


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read."""
    success = await AlertService.mark_notification_read(db, notification_id, current_user.id)
    if not success:
        raise NotFoundError(resource="Notification", resource_id=notification_id)
    return {"status": "ok"}


# ─── Alert CRUD (/{alert_id} routes come AFTER static paths) ──
@router.get("/{alert_id}", response_model=AlertOut)
async def get_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single alert by ID."""
    alert = await AlertService.get_by_id(db, alert_id, current_user.org_id)
    if not alert:
        raise NotFoundError(resource="Alert", resource_id=alert_id)
    return AlertOut.model_validate(alert)


@router.patch("/{alert_id}", response_model=AlertOut)
async def update_alert(
    alert_id: str,
    data: AlertUpdate,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """Update alert configuration, threshold, or status."""
    alert = await AlertService.update(db, alert_id, current_user.org_id, data)
    if not alert:
        raise NotFoundError(resource="Alert", resource_id=alert_id)
    return AlertOut.model_validate(alert)


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """Delete an alert rule and its history."""
    success = await AlertService.delete(db, alert_id, current_user.org_id)
    if not success:
        raise NotFoundError(resource="Alert", resource_id=alert_id)


@router.post("/{alert_id}/mute", response_model=AlertOut)
async def mute_alert(
    alert_id: str,
    data: MuteAlertRequest,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """Mute an alert for a specified number of minutes."""
    alert = await AlertService.mute(db, alert_id, current_user.org_id, data.minutes)
    if not alert:
        raise NotFoundError(resource="Alert", resource_id=alert_id)
    return AlertOut.model_validate(alert)


@router.get("/{alert_id}/history", response_model=list[AlertHistoryOut])
async def get_alert_history(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get trigger/resolve history for an alert."""
    # Verify alert exists and belongs to org
    alert = await AlertService.get_by_id(db, alert_id, current_user.org_id)
    if not alert:
        raise NotFoundError(resource="Alert", resource_id=alert_id)
    history = await AlertService.get_history(db, alert_id)
    return [AlertHistoryOut.model_validate(h) for h in history]
