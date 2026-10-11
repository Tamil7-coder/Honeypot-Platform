from datetime import datetime

from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password_configured: bool  # never expose the password itself, encrypted or not
    smtp_use_tls: bool
    smtp_from_email: str
    smtp_from_name: str
    email_enabled: bool

    admin_alert_email: str
    alert_min_severity: str

    theme: str
    session_timeout_minutes: int
    retention_policy_days: int

    updated_at: datetime


class SettingsUpdateRequest(BaseModel):
    """All fields optional: only provided fields are changed. smtp_password
    is write-only -- omit it to keep the currently-stored password, or send
    an empty string to clear it."""

    smtp_host: str | None = None
    smtp_port: int | None = Field(None, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool | None = None
    smtp_from_email: str | None = None
    smtp_from_name: str | None = None
    email_enabled: bool | None = None

    admin_alert_email: str | None = None
    alert_min_severity: str | None = Field(None, pattern="^(low|medium|high|critical)$")

    theme: str | None = Field(None, pattern="^(dark|light)$")
    session_timeout_minutes: int | None = Field(None, ge=5, le=10080)
    retention_policy_days: int | None = Field(None, ge=1, le=3650)


class RetentionCleanupResponse(BaseModel):
    deleted_sessions: int
    retention_policy_days: int


class TestEmailRequest(BaseModel):
    to_email: str


class TestEmailResponse(BaseModel):
    success: bool
    detail: str
