import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.attack import Alert


class AlertRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, alert: Alert) -> Alert:
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def mark_email_result(self, alert: Alert, *, sent: bool, error: str | None = None) -> Alert:
        alert.email_sent = sent
        alert.email_error = error
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def list_recent(self, limit: int = 10) -> list[Alert]:
        stmt = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    # --- Phase 11: Notification Center ---

    def get_by_id(self, alert_id: uuid.UUID) -> Alert | None:
        return self.db.get(Alert, alert_id)

    def list_notifications(
        self, skip: int = 0, limit: int = 30, include_dismissed: bool = False
    ) -> tuple[int, list[Alert]]:
        stmt = select(Alert)
        if not include_dismissed:
            stmt = stmt.where(Alert.dismissed_at.is_(None))

        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        stmt = stmt.order_by(Alert.created_at.desc()).offset(skip).limit(limit)
        items = list(self.db.execute(stmt).scalars().all())
        return total, items

    def count_unread(self) -> int:
        stmt = (
            select(func.count())
            .select_from(Alert)
            .where(Alert.is_read.is_(False), Alert.dismissed_at.is_(None))
        )
        return self.db.execute(stmt).scalar_one()

    def mark_read(self, alert: Alert) -> Alert:
        alert.is_read = True
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def mark_all_read(self) -> int:
        stmt = select(Alert).where(Alert.is_read.is_(False), Alert.dismissed_at.is_(None))
        unread = list(self.db.execute(stmt).scalars().all())
        for alert in unread:
            alert.is_read = True
        self.db.commit()
        return len(unread)

    def dismiss(self, alert: Alert) -> Alert:
        alert.dismissed_at = datetime.now(timezone.utc)
        alert.is_read = True
        self.db.commit()
        self.db.refresh(alert)
        return alert
