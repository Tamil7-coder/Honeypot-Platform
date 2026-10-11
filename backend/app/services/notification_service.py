import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.attack import Alert
from app.repositories.alert_repository import AlertRepository
from app.schemas.notification import NotificationItem, NotificationListResponse


def _to_item(alert: Alert) -> NotificationItem:
    return NotificationItem(
        id=alert.id,
        severity=alert.severity.value,
        title=alert.title,
        message=alert.message,
        source_ip=str(alert.source_ip) if alert.source_ip else None,
        email_sent=alert.email_sent,
        email_error=alert.email_error,
        is_read=alert.is_read,
        dismissed_at=alert.dismissed_at,
        created_at=alert.created_at,
    )


class NotificationService:
    def __init__(self, db: Session):
        self.repo = AlertRepository(db)

    def list_notifications(self, skip: int, limit: int, include_dismissed: bool) -> NotificationListResponse:
        total, items = self.repo.list_notifications(skip=skip, limit=limit, include_dismissed=include_dismissed)
        return NotificationListResponse(
            total=total,
            unread_count=self.repo.count_unread(),
            items=[_to_item(a) for a in items],
        )

    def unread_count(self) -> int:
        return self.repo.count_unread()

    def mark_read(self, alert_id: uuid.UUID) -> NotificationItem:
        alert = self.repo.get_by_id(alert_id)
        if alert is None:
            raise NotFoundError("Notification not found")
        return _to_item(self.repo.mark_read(alert))

    def dismiss(self, alert_id: uuid.UUID) -> NotificationItem:
        alert = self.repo.get_by_id(alert_id)
        if alert is None:
            raise NotFoundError("Notification not found")
        return _to_item(self.repo.dismiss(alert))

    def mark_all_read(self) -> int:
        return self.repo.mark_all_read()
