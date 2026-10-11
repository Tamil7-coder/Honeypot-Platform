"""
SMTP email delivery.

Deliberately uses stdlib `smtplib` rather than a third-party mail SDK -- this
keeps the platform provider-agnostic (Gmail, Mailtrap, Office365, a
corporate relay, etc. are all just SMTP with different host/port/credentials)
and avoids adding a dependency whose API might not match every provider.

Phase 12: takes its SMTP configuration as an explicit parameter object
rather than reading the static app.core.config.settings singleton
internally. This is what lets the Settings page's changes take effect
without a restart -- callers (AlertService) fetch the current config from
the database and pass it in here, instead of this service silently always
using whatever was in .env at process startup.
"""
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class SmtpConfig:
    enabled: bool
    host: str
    port: int
    username: str
    password: str | None
    use_tls: bool
    from_email: str
    from_name: str


class EmailDeliveryError(Exception):
    """Raised when an SMTP send fails. Callers should catch this and degrade
    gracefully (log + record the failure) rather than let it propagate into
    request/ingestion flows."""


class EmailService:
    @staticmethod
    def is_configured(config: SmtpConfig) -> bool:
        return bool(config.enabled and config.username and config.password)

    def send(self, config: SmtpConfig, *, to_email: str, subject: str, html_body: str, text_body: str) -> None:
        if not self.is_configured(config):
            logger.warning(
                "Email not sent (enabled=%s, credentials configured=%s): subject=%r",
                config.enabled,
                bool(config.username and config.password),
                subject,
            )
            raise EmailDeliveryError("SMTP is not configured (set it in Settings or .env)")

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{config.from_name} <{config.from_email}>"
        message["To"] = to_email
        message.attach(MIMEText(text_body, "plain"))
        message.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(config.host, config.port, timeout=10) as server:
                if config.use_tls:
                    server.starttls()
                server.login(config.username, config.password)
                server.sendmail(config.from_email, [to_email], message.as_string())
            logger.info("Alert email sent to %s: %s", to_email, subject)
        except (smtplib.SMTPException, OSError) as exc:
            logger.error("Failed to send alert email to %s: %s", to_email, exc)
            raise EmailDeliveryError(str(exc)) from exc
