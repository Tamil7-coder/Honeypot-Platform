import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class HoneypotType(str, enum.Enum):
    COWRIE = "cowrie"
    OPENCANARY = "opencanary"
    DIONAEA = "dionaea"
    CONPOT = "conpot"
    MAILONEY = "mailoney"


class Severity(str, enum.Enum):
    """Attack severity classification.

    Populated today by a minimal rule-based heuristic (RiskScoringService).
    Phase 7 replaces that heuristic's internals with a full weighted risk
    engine — this enum and every column/schema that uses it stays exactly
    the same, so that upgrade is a drop-in replacement, not a rewrite.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Honeypot(Base):
    """Represents a deployed honeypot sensor."""

    __tablename__ = "honeypots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    honeypot_type: Mapped[HoneypotType] = mapped_column(
        String(50), nullable=False
    )
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sessions: Mapped[list["AttackSession"]] = relationship(back_populates="honeypot")


class AttackSession(Base):
    """A single attacker session captured by a honeypot."""

    __tablename__ = "attack_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    honeypot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("honeypots.id"), nullable=False)
    session_ref: Mapped[str] = mapped_column(String(128), nullable=False)  # e.g. cowrie session id

    source_ip: Mapped[str] = mapped_column(INET, nullable=False, index=True)
    source_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    destination_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protocol: Mapped[str] = mapped_column(String(20), nullable=False)  # ssh/telnet/http/ftp...
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    severity: Mapped[Severity | None] = mapped_column(
        Enum(Severity, name="severity_enum", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=True,
        index=True,
    )
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    honeypot: Mapped["Honeypot"] = relationship(back_populates="sessions")
    login_attempts: Mapped[list["LoginAttempt"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    commands: Mapped[list["Command"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    files: Mapped[list["File"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_attack_sessions_started_at", "started_at"),
        Index("ix_attack_sessions_source_ip_started_at", "source_ip", "started_at"),
    )


class LoginAttempt(Base):
    """Credential pairs attempted against a honeypot session."""

    __tablename__ = "login_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("attack_sessions.id"), nullable=False)

    username: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    success: Mapped[bool] = mapped_column(default=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["AttackSession"] = relationship(back_populates="login_attempts")


class Command(Base):
    """A discrete protocol-level interaction within a session.

    Originally "shell commands executed by an attacker" (Cowrie SSH/Telnet).
    Generalized for multi-honeypot support: the same table now also holds
    an HTTP request (Dionaea), an FTP command, a DNS query, a Modbus
    function call, etc. `command_text` stays a human-readable summary (so
    Attack Replay, Top Commands analytics, and Advanced Search's command
    filter keep working unchanged for every protocol); `metadata` carries
    the structured, protocol-specific fields (HTTP method/path/headers,
    Modbus function code/register, DNS query type...) for richer display
    without needing a new table per protocol.
    """

    __tablename__ = "commands"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("attack_sessions.id"), nullable=False)

    command_text: Mapped[str] = mapped_column(Text, nullable=False)
    command_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["AttackSession"] = relationship(back_populates="commands")


class FileDirection(str, enum.Enum):
    DOWNLOAD = "download"
    UPLOAD = "upload"


class File(Base):
    """A file transferred during an attack session — either downloaded by
    the attacker (e.g. via wget/curl, or Cowrie's file_download event) or
    uploaded to the honeypot (e.g. via SCP/SFTP, Cowrie's file_upload
    event). Distinct from raw Command text so the Attack Replay timeline
    (Phase 8) can show a structured "Downloaded x.sh (2.3KB)" step rather
    than just the shell command that triggered it.
    """

    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("attack_sessions.id"), nullable=False)

    direction: Mapped[FileDirection] = mapped_column(
        Enum(FileDirection, name="file_direction_enum", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)  # source URL, for downloads
    filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["AttackSession"] = relationship(back_populates="files")


class AuditLog(Base):
    """Immutable record of security-relevant actions taken within the platform itself."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IpReputation(Base):
    """Cached threat-intelligence lookup for an attacker IP.

    Raw provider responses are stored as JSONB rather than individual
    columns: each provider's schema is external and can evolve, and not
    every session has data from every provider (a lookup can succeed for
    AbuseIPDB while VirusTotal is unconfigured or times out). Storing raw
    JSON plus a derived `threat_level` keeps the schema stable while still
    letting ThreatIntelService normalize the response for the API/frontend.

    Cached for THREAT_INTEL_CACHE_HOURS (default 24h) to avoid burning
    through free-tier rate limits on repeated lookups of the same IP.
    """

    __tablename__ = "ip_reputation"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip_address: Mapped[str] = mapped_column(INET, unique=True, nullable=False, index=True)

    abuseipdb_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    virustotal_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    otx_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    geolocation_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    threat_level: Mapped[Severity | None] = mapped_column(
        Enum(Severity, name="severity_enum", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=True,
    )

    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Alert(Base):
    """A security alert raised for a HIGH/CRITICAL attack session.

    Created by AlertService whenever RiskScoringService classifies a session
    at or above the configured threshold. `email_sent`/`email_error` track
    delivery outcome so failed SMTP sends are visible without crashing
    ingestion. `is_read`/`dismissed_at` (Phase 11) back the Notification
    Center rather than a parallel model.
    """

    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("attack_sessions.id"), nullable=True)

    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity_enum", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source_ip: Mapped[str | None] = mapped_column(INET, nullable=True)

    email_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    session: Mapped["AttackSession | None"] = relationship(back_populates="alerts")
