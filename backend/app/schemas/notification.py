import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationItem(BaseModel):
    id: uuid.UUID
    severity: str
    title: str
    message: str
    source_ip: str | None
    email_sent: bool
    email_error: str | None
    is_read: bool
    dismissed_at: datetime | None
    created_at: datetime


class NotificationListResponse(BaseModel):
    total: int
    unread_count: int
    items: list[NotificationItem]


class UnreadCountResponse(BaseModel):
    unread_count: int
