"""
Report data layer (Phase 9).

`ReportService.build()` is the single place that decides *what* goes in a
report; csv_exporter/excel_exporter/pdf_exporter each just decide *how* to
render the same ReportData. This keeps the three export formats from
drifting out of sync with each other.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.attack import AttackSession
from app.repositories.attack_repository import AttackRepository

ReportPeriod = Literal["daily", "weekly", "monthly"]


@dataclass
class ReportData:
    period_label: str
    since: datetime
    until: datetime
    generated_at: datetime
    total_attacks: int
    unique_attacker_ips: int
    severity_breakdown: list[dict]
    top_attacker_ips: list[dict]
    top_countries: list[dict]
    top_credentials: list[dict]
    sessions: list[AttackSession] = field(default_factory=list)


def resolve_period(period: ReportPeriod) -> tuple[datetime, datetime, str]:
    now = datetime.now(timezone.utc)
    if period == "daily":
        since = now - timedelta(days=1)
        label = f"Daily Report — {now.strftime('%Y-%m-%d')}"
    elif period == "weekly":
        since = now - timedelta(weeks=1)
        label = f"Weekly Report — {since.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}"
    elif period == "monthly":
        since = now - timedelta(days=30)
        label = f"Monthly Report — {since.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}"
    else:
        raise AppException(f"Unknown report period: {period}", status_code=400)
    return since, now, label


class ReportService:
    def __init__(self, db: Session):
        self.repo = AttackRepository(db)

    def build(self, period: ReportPeriod) -> ReportData:
        since, until, label = resolve_period(period)

        summary = self.repo.report_summary(since, until)

        return ReportData(
            period_label=label,
            since=since,
            until=until,
            generated_at=datetime.now(timezone.utc),
            total_attacks=summary["total_attacks"],
            unique_attacker_ips=summary["unique_attacker_ips"],
            severity_breakdown=self.repo.report_severity_breakdown(since, until),
            top_attacker_ips=self.repo.report_top_attacker_ips(since, until),
            top_countries=self.repo.report_top_countries(since, until),
            top_credentials=self.repo.report_top_credentials(since, until),
            sessions=self.repo.report_sessions(since, until),
        )
