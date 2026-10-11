"""phase 12: add platform_settings table

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-27

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.config import settings as app_settings

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("smtp_host", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("smtp_port", sa.Integer(), nullable=False, server_default="587"),
        sa.Column("smtp_username", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("smtp_password_encrypted", sa.String(length=1024), nullable=True),
        sa.Column("smtp_use_tls", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("smtp_from_email", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("smtp_from_name", sa.String(length=255), nullable=False, server_default="Honeynet SOC"),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("admin_alert_email", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("alert_min_severity", sa.String(length=20), nullable=False, server_default="high"),
        sa.Column("theme", sa.String(length=20), nullable=False, server_default="dark"),
        sa.Column("session_timeout_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("retention_policy_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Seed the single settings row from current .env values so existing
    # deployments keep behaving identically until an admin changes something
    # via the new Settings page. SMTP password is encrypted before storage,
    # same as it would be via the Settings API.
    from app.core.crypto import encrypt_secret  # local import: only needed for this one-time seed

    conn = op.get_bind()
    encrypted_password = encrypt_secret(app_settings.SMTP_PASSWORD) if app_settings.SMTP_PASSWORD else None

    conn.execute(
        sa.text(
            """
            INSERT INTO platform_settings (
                id, smtp_host, smtp_port, smtp_username, smtp_password_encrypted, smtp_use_tls,
                smtp_from_email, smtp_from_name, email_enabled, admin_alert_email, alert_min_severity,
                theme, session_timeout_minutes, retention_policy_days
            ) VALUES (
                :id, :smtp_host, :smtp_port, :smtp_username, :smtp_password_encrypted, :smtp_use_tls,
                :smtp_from_email, :smtp_from_name, :email_enabled, :admin_alert_email, :alert_min_severity,
                'dark', :session_timeout_minutes, 90
            )
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "smtp_host": app_settings.SMTP_HOST,
            "smtp_port": app_settings.SMTP_PORT,
            "smtp_username": app_settings.SMTP_USERNAME,
            "smtp_password_encrypted": encrypted_password,
            "smtp_use_tls": app_settings.SMTP_USE_TLS,
            "smtp_from_email": app_settings.SMTP_FROM_EMAIL,
            "smtp_from_name": app_settings.SMTP_FROM_NAME,
            "email_enabled": app_settings.EMAIL_ENABLED,
            "admin_alert_email": app_settings.ADMIN_ALERT_EMAIL,
            "alert_min_severity": app_settings.ALERT_MIN_SEVERITY,
            "session_timeout_minutes": app_settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        },
    )


def downgrade() -> None:
    op.drop_table("platform_settings")
