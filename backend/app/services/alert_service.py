from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alert import Alert, AlertHistory, AlertStatus, Notification
from app.models.event import Event
from app.schemas.alert import AlertCreate, AlertUpdate


class AlertService:

    @staticmethod
    async def create(db: AsyncSession, org_id: str, user_id: str, data: AlertCreate) -> Alert:
        alert = Alert(
            org_id=org_id,
            name=data.name,
            description=data.description,
            event_name=data.event_name,
            metric=data.metric,
            operator=data.operator,
            threshold=data.threshold,
            window_minutes=data.window_minutes,
            channels=data.channels,
            created_by=user_id,
        )
        db.add(alert)
        await db.flush()
        return alert

    @staticmethod
    async def list_all(db: AsyncSession, org_id: str):
        result = await db.execute(
            select(Alert).where(Alert.org_id == org_id).order_by(Alert.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, alert_id: str, org_id: str) -> Alert | None:
        result = await db.execute(
            select(Alert).where(Alert.id == alert_id, Alert.org_id == org_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update(db: AsyncSession, alert_id: str, org_id: str, data: AlertUpdate) -> Alert | None:
        alert = await AlertService.get_by_id(db, alert_id, org_id)
        if not alert:
            return None
        for field, val in data.model_dump(exclude_unset=True).items():
            setattr(alert, field, val)
        await db.flush()
        return alert

    @staticmethod
    async def delete(db: AsyncSession, alert_id: str, org_id: str) -> bool:
        alert = await AlertService.get_by_id(db, alert_id, org_id)
        if not alert:
            return False
        await db.delete(alert)
        await db.flush()
        return True

    @staticmethod
    async def mute(db: AsyncSession, alert_id: str, org_id: str, minutes: int) -> Alert | None:
        alert = await AlertService.get_by_id(db, alert_id, org_id)
        if not alert:
            return None
        alert.status = AlertStatus.MUTED
        alert.muted_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        await db.flush()
        return alert

    @staticmethod
    async def get_history(db: AsyncSession, alert_id: str):
        result = await db.execute(
            select(AlertHistory).where(AlertHistory.alert_id == alert_id).order_by(AlertHistory.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def evaluate_alert(db: AsyncSession, alert: Alert) -> tuple[bool, float]:
        """Evaluate an alert rule against recent events. Returns (triggered, value)."""
        now = datetime.now(timezone.utc)

        # Check mute
        if alert.status == AlertStatus.MUTED and alert.muted_until and alert.muted_until > now:
            return False, 0.0

        window_start = now - timedelta(minutes=alert.window_minutes)

        agg = func.count(Event.id)
        if alert.metric == "unique":
            agg = func.count(func.distinct(Event.user_id))

        result = await db.execute(
            select(agg).where(
                Event.org_id == alert.org_id,
                Event.name == alert.event_name,
                Event.created_at >= window_start,
                Event.created_at <= now,
            )
        )
        value = float(result.scalar() or 0)

        ops = {
            ">": lambda v, t: v > t,
            "<": lambda v, t: v < t,
            ">=": lambda v, t: v >= t,
            "<=": lambda v, t: v <= t,
            "==": lambda v, t: v == t,
        }
        check = ops.get(alert.operator, ops[">"])
        triggered = check(value, alert.threshold)

        if triggered:
            alert.status = AlertStatus.TRIGGERED
            alert.last_triggered_at = now
            history = AlertHistory(
                alert_id=alert.id,
                status="triggered",
                triggered_value=value,
                message=f"{alert.event_name} {alert.metric} = {value} {alert.operator} {alert.threshold}",
            )
            db.add(history)
            await db.flush()
        elif alert.status == AlertStatus.TRIGGERED:
            alert.status = AlertStatus.RESOLVED
            history = AlertHistory(
                alert_id=alert.id,
                status="resolved",
                triggered_value=value,
                message=f"Resolved: {alert.event_name} {alert.metric} = {value}",
            )
            db.add(history)
            await db.flush()

        return triggered, value

    @staticmethod
    async def get_notifications(db: AsyncSession, user_id: str, unread_only: bool = False):
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.is_read == False)
        query = query.order_by(Notification.created_at.desc()).limit(50)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def mark_notification_read(db: AsyncSession, notification_id: str, user_id: str) -> bool:
        result = await db.execute(
            select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
        )
        notif = result.scalar_one_or_none()
        if not notif:
            return False
        notif.is_read = True
        await db.flush()
        return True
