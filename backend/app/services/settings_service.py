from sqlalchemy.orm import Session

from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.logging_config import get_logger
from app.repositories.attack_repository import AttackRepository
from app.repositories.settings_repository import SettingsRepository
from app.schemas.settings import (
    RetentionCleanupResponse,
    SettingsResponse,
    SettingsUpdateRequest,
    TestEmailResponse,
)
from app.services.email_service import EmailDeliveryError, EmailService, SmtpConfig

logger = get_logger(__name__)


def _to_response(row) -> SettingsResponse:
    return SettingsResponse(
        smtp_host=row.smtp_host,
        smtp_port=row.smtp_port,
        smtp_username=row.smtp_username,
        smtp_password_configured=bool(row.smtp_password_encrypted),
        smtp_use_tls=row.smtp_use_tls,
        smtp_from_email=row.smtp_from_email,
        smtp_from_name=row.smtp_from_name,
        email_enabled=row.email_enabled,
        admin_alert_email=row.admin_alert_email,
        alert_min_severity=row.alert_min_severity,
        theme=row.theme,
        session_timeout_minutes=row.session_timeout_minutes,
        retention_policy_days=row.retention_policy_days,
        updated_at=row.updated_at,
    )


def _smtp_config(row) -> SmtpConfig:
    return SmtpConfig(
        enabled=row.email_enabled,
        host=row.smtp_host,
        port=row.smtp_port,
        username=row.smtp_username,
        password=decrypt_secret(row.smtp_password_encrypted) if row.smtp_password_encrypted else None,
        use_tls=row.smtp_use_tls,
        from_email=row.smtp_from_email,
        from_name=row.smtp_from_name,
    )


class SettingsService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SettingsRepository(db)
        self.attack_repo = AttackRepository(db)

    def get_settings(self) -> SettingsResponse:
        return _to_response(self.repo.get())

    def update_settings(self, payload: SettingsUpdateRequest) -> SettingsResponse:
        row = self.repo.get()

        updates = payload.model_dump(exclude_unset=True, exclude={"smtp_password"})
        for field, value in updates.items():
            setattr(row, field, value)

        # smtp_password is handled separately: omitted = keep current,
        # empty string = clear, non-empty = encrypt and store.
        if "smtp_password" in payload.model_fields_set:
            row.smtp_password_encrypted = encrypt_secret(payload.smtp_password) if payload.smtp_password else None

        row = self.repo.save(row)
        logger.info("Platform settings updated")
        return _to_response(row)

    def run_retention_cleanup(self) -> RetentionCleanupResponse:
        row = self.repo.get()
        deleted = self.attack_repo.purge_sessions_older_than(row.retention_policy_days)
        logger.info("Retention cleanup: deleted %d sessions older than %d days", deleted, row.retention_policy_days)
        return RetentionCleanupResponse(deleted_sessions=deleted, retention_policy_days=row.retention_policy_days)

    def send_test_email(self, to_email: str) -> TestEmailResponse:
        row = self.repo.get()
        config = _smtp_config(row)
        email_service = EmailService()

        if not email_service.is_configured(config):
            return TestEmailResponse(
                success=False, detail="SMTP is not fully configured (enable it and set credentials)."
            )

        try:
            email_service.send(
                config,
                to_email=to_email,
                subject="Honeynet SOC — Test Email",
                html_body="<p>This is a test email from your Honeynet SOC platform. SMTP is configured correctly.</p>",
                text_body="This is a test email from your Honeynet SOC platform. SMTP is configured correctly.",
            )
            return TestEmailResponse(success=True, detail=f"Test email sent to {to_email}.")
        except EmailDeliveryError as exc:
            return TestEmailResponse(success=False, detail=str(exc))
