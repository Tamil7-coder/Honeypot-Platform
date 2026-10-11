import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlatformSettings(Base):
    """Single-row table of admin-configurable runtime settings (Phase 12).

    Seeded once from the .env defaults on first startup (see bootstrap.py);
    after that, the database is authoritative and .env values are only the
    fallback used to seed the initial row. This is what makes Settings
    changes actually take effect without a restart -- EmailService and
    AlertService read from here (via SettingsRepository) rather than from
    the static app.core.config.settings singleton for the fields this page
    makes configurable.
    """

    __tablename__ = "platform_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # SMTP
    smtp_host: Mapped[str] = mapped_column(String(255), default="")
    smtp_port: Mapped[int] = mapped_column(Integer, default=587)
    smtp_username: Mapped[str] = mapped_column(String(255), default="")
    smtp_password_encrypted: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    smtp_use_tls: Mapped[bool] = mapped_column(Boolean, default=True)
    smtp_from_email: Mapped[str] = mapped_column(String(255), default="")
    smtp_from_name: Mapped[str] = mapped_column(String(255), default="Honeynet SOC")
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Alerts
    admin_alert_email: Mapped[str] = mapped_column(String(255), default="")
    alert_min_severity: Mapped[str] = mapped_column(String(20), default="high")

    # Application preferences
    theme: Mapped[str] = mapped_column(String(20), default="dark")
    session_timeout_minutes: Mapped[int] = mapped_column(Integer, default=60)
    retention_policy_days: Mapped[int] = mapped_column(Integer, default=90)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
