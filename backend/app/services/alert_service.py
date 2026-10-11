import uuid

from app.core.crypto import decrypt_secret
from app.core.logging_config import get_logger
from app.db.session import SessionLocal
from app.models.attack import Alert, AttackSession, Severity
from app.repositories.alert_repository import AlertRepository
from app.repositories.settings_repository import SettingsRepository
from app.services.connection_manager import connection_manager
from app.services.email_service import EmailDeliveryError, EmailService, SmtpConfig
from app.services.email_templates import build_attack_alert_email
from app.services.risk_scoring_service import meets_threshold

logger = get_logger(__name__)


def _smtp_config_from_settings(platform_settings) -> SmtpConfig:
    return SmtpConfig(
        enabled=platform_settings.email_enabled,
        host=platform_settings.smtp_host,
        port=platform_settings.smtp_port,
        username=platform_settings.smtp_username,
        password=decrypt_secret(platform_settings.smtp_password_encrypted)
        if platform_settings.smtp_password_encrypted
        else None,
        use_tls=platform_settings.smtp_use_tls,
        from_email=platform_settings.smtp_from_email,
        from_name=platform_settings.smtp_from_name,
    )


class AlertService:
    def __init__(self, email_service: EmailService | None = None):
        self.email_service = email_service or EmailService()

    @staticmethod
    def should_alert(severity: Severity | None, min_severity: str) -> bool:
        """
        Phase 12: the threshold is passed in by the caller (fetched fresh
        from the database on every ingestion) rather than read from static
        config, so changing "Notification Threshold" in Settings takes
        effect on the very next attack -- no restart needed.
        """
        if severity is None:
            return False
        try:
            threshold = Severity(min_severity.lower())
        except ValueError:
            logger.error("Invalid alert_min_severity=%r in settings; defaulting to HIGH", min_severity)
            threshold = Severity.HIGH
        return meets_threshold(severity, threshold)

    def create_and_send_alert(self, session_id: uuid.UUID) -> None:
        """
        Runs as a FastAPI BackgroundTask *after* the originating request's DB
        session has already closed -- so it opens and owns its own session
        rather than reusing one injected via `Depends(get_db)`. This method
        never raises: ingestion must never be affected by an alert/email
        failure downstream of it.
        """
        db = SessionLocal()
        try:
            session = db.get(AttackSession, session_id)
            if session is None:
                logger.warning("AlertService: session %s not found (already deleted?)", session_id)
                return

            platform_settings = SettingsRepository(db).get()
            smtp_config = _smtp_config_from_settings(platform_settings)

            login_attempts = [
                {"username": a.username, "password": a.password, "success": a.success}
                for a in session.login_attempts
            ]
            command_texts = [c.command_text for c in session.commands]

            title = f"{(session.severity or Severity.LOW).value.upper()} attack from {session.source_ip}"
            message = (
                f"{session.protocol.upper()} session from {session.source_ip} "
                f"({session.country_code or 'unknown'}) -- "
                f"{len(login_attempts)} login attempt(s), {len(command_texts)} command(s) executed."
            )

            alert_repo = AlertRepository(db)
            alert = alert_repo.create(
                Alert(
                    session_id=session.id,
                    severity=session.severity or Severity.LOW,
                    title=title,
                    message=message,
                    source_ip=session.source_ip,
                )
            )

            connection_manager.broadcast_sync(
                {
                    "type": "new_alert",
                    "data": {
                        "id": str(alert.id),
                        "severity": alert.severity.value,
                        "title": alert.title,
                        "message": alert.message,
                        "source_ip": str(alert.source_ip) if alert.source_ip else None,
                        "created_at": alert.created_at.isoformat(),
                    },
                }
            )

            if not self.email_service.is_configured(smtp_config):
                alert_repo.mark_email_result(alert, sent=False, error="SMTP not configured")
                return

            if not platform_settings.admin_alert_email:
                alert_repo.mark_email_result(alert, sent=False, error="Admin alert email not set")
                return

            subject, html_body, text_body = build_attack_alert_email(
                session=session, login_attempts=login_attempts, command_texts=command_texts
            )

            try:
                self.email_service.send(
                    smtp_config,
                    to_email=platform_settings.admin_alert_email,
                    subject=subject,
                    html_body=html_body,
                    text_body=text_body,
                )
                alert_repo.mark_email_result(alert, sent=True)
            except EmailDeliveryError as exc:
                alert_repo.mark_email_result(alert, sent=False, error=str(exc))
        except Exception:  # noqa: BLE001 - background task must never crash the process
            logger.exception("Unexpected error while creating/sending alert for session %s", session_id)
        finally:
            db.close()
