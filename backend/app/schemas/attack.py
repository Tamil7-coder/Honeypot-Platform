import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress


class LoginAttemptIngest(BaseModel):
    username: str = Field(..., max_length=255)
    password: str = Field(..., max_length=255)
    success: bool = False


class CommandIngest(BaseModel):
    command_text: str
    command_metadata: dict | None = None


class FileIngest(BaseModel):
    direction: str = Field(..., pattern="^(download|upload)$")
    url: str | None = None
    filename: str | None = None
    file_size: int | None = None
    sha256: str | None = None


class AttackSessionIngest(BaseModel):
    """
    Payload accepted from a honeypot log-shipper (e.g. Cowrie JSON log parser).
    This is the single ingestion contract all honeypot adapters must conform to.
    """

    honeypot_name: str
    session_ref: str
    source_ip: IPvAnyAddress
    source_port: int | None = None
    destination_port: int | None = None
    protocol: str = Field(..., max_length=20)
    country_code: str | None = Field(None, max_length=2)
    started_at: datetime
    ended_at: datetime | None = None
    login_attempts: list[LoginAttemptIngest] = []
    commands: list[CommandIngest] = []
    files: list[FileIngest] = []


class AttackSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    honeypot_id: uuid.UUID
    session_ref: str
    source_ip: str
    protocol: str
    country_code: str | None
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
    severity: str | None = None
    risk_score: int | None = None


class AttackSessionListResponse(BaseModel):
    total: int
    items: list[AttackSessionResponse]


class ReplayEvent(BaseModel):
    """A single normalized step in the attack replay timeline. `event_type`
    is one of: login_success, login_failed, command, download, upload,
    disconnect — the frontend renders each type with its own icon/styling."""

    event_type: str
    timestamp: datetime
    detail: dict


class AttackReplayResponse(BaseModel):
    session: AttackSessionResponse
    timeline: list[ReplayEvent]


class HoneypotStatusItem(BaseModel):
    name: str
    type: str
    is_active: bool
    session_count: int


class AlertItem(BaseModel):
    id: uuid.UUID
    severity: str
    title: str
    message: str
    source_ip: str | None
    email_sent: bool
    created_at: datetime


class SessionDurationStats(BaseModel):
    avg_seconds: float | None
    min_seconds: int | None
    max_seconds: int | None
    median_seconds: float | None


class AdvancedAnalyticsResponse(BaseModel):
    hourly_distribution: list[dict]
    attack_heatmap: list[dict]
    weekly_trend: list[dict]
    monthly_trend: list[dict]
    top_commands: list[dict]
    session_duration: SessionDurationStats
    risk_distribution: list[dict]


class DashboardSummaryResponse(BaseModel):
    total_attacks: int
    active_sessions_last_hour: int
    unique_attacker_ips: int
    top_targeted_services: list[dict]
    top_attacker_ips: list[dict]
    attacks_last_7_days: list[dict]

    # Phase 1 UI redesign additions — additive, backward compatible
    active_honeypots: int
    total_honeypots: int
    attacks_today: int
    top_countries: list[dict]
    top_usernames: list[dict]
    top_passwords: list[dict]
    honeypot_status: list[HoneypotStatusItem]

    # Phase 3 addition — real alert data
    recent_alerts: list[AlertItem]

    # Phase 7 addition — real risk scoring engine output
    avg_risk_score_24h: float | None
    risk_score_sample_size: int
