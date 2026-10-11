import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.notification import NotificationItem, NotificationListResponse, UnreadCountResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notification Center"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    skip: int = 0,
    limit: int = Query(30, le=100),
    include_dismissed: bool = False,
    db: Session = Depends(get_db),
):
    service = NotificationService(db)
    return service.list_notifications(skip=skip, limit=limit, include_dismissed=include_dismissed)


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(db: Session = Depends(get_db)):
    service = NotificationService(db)
    return UnreadCountResponse(unread_count=service.unread_count())


@router.patch("/{notification_id}/read", response_model=NotificationItem)
def mark_read(notification_id: uuid.UUID, db: Session = Depends(get_db)):
    service = NotificationService(db)
    return service.mark_read(notification_id)


@router.patch("/{notification_id}/dismiss", response_model=NotificationItem)
def dismiss_notification(notification_id: uuid.UUID, db: Session = Depends(get_db)):
    service = NotificationService(db)
    return service.dismiss(notification_id)


@router.post("/mark-all-read")
def mark_all_read(db: Session = Depends(get_db)):
    service = NotificationService(db)
    count = service.mark_all_read()
    return {"marked_read": count}
