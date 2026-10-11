from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.repositories.alert_repository import AlertRepository
from app.repositories.attack_repository import AttackRepository
from app.schemas.attack import AdvancedAnalyticsResponse, AlertItem, DashboardSummaryResponse, SessionDurationStats


class AnalyticsService:
    """Computes aggregate attack metrics for the SOC dashboard.

    Kept separate from AttackService (which owns raw ingestion/CRUD) so that
    analytics queries - which are read-heavy and may later be moved to a
    materialized view or a caching layer - can evolve independently.
    """

    def __init__(self, db: Session):
        self.repo = AttackRepository(db)
        self.alert_repo = AlertRepository(db)

    def get_dashboard_summary(self) -> DashboardSummaryResponse:
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        risk_stats = self.repo.avg_risk_score_last_24h()
        return DashboardSummaryResponse(
            total_attacks=self.repo.count_total_sessions(),
            active_sessions_last_hour=self.repo.count_active_sessions_since(one_hour_ago),
            unique_attacker_ips=self.repo.count_unique_attacker_ips(),
            top_targeted_services=self.repo.top_targeted_services(),
            top_attacker_ips=self.repo.top_attacker_ips(),
            attacks_last_7_days=self.repo.attacks_per_day(days=7),
            active_honeypots=self.repo.count_active_honeypots(),
            total_honeypots=self.repo.count_total_honeypots(),
            attacks_today=self.repo.count_attacks_today(),
            top_countries=self.repo.top_countries(),
            top_usernames=self.repo.top_usernames(),
            top_passwords=self.repo.top_passwords(),
            honeypot_status=self.repo.honeypot_status(),
            recent_alerts=[
                AlertItem(
                    id=a.id,
                    severity=a.severity.value,
                    title=a.title,
                    message=a.message,
                    source_ip=str(a.source_ip) if a.source_ip else None,
                    email_sent=a.email_sent,
                    created_at=a.created_at,
                )
                for a in self.alert_repo.list_recent(limit=10)
            ],
            avg_risk_score_24h=risk_stats["avg_risk_score"],
            risk_score_sample_size=risk_stats["sample_size"],
        )

    def get_advanced_analytics(self) -> AdvancedAnalyticsResponse:
        duration = self.repo.session_duration_stats()
        return AdvancedAnalyticsResponse(
            hourly_distribution=self.repo.hourly_distribution(),
            attack_heatmap=self.repo.attack_heatmap(),
            weekly_trend=self.repo.weekly_trend(weeks=8),
            monthly_trend=self.repo.monthly_trend(months=6),
            top_commands=self.repo.top_commands(),
            session_duration=SessionDurationStats(**duration),
            risk_distribution=self.repo.risk_distribution(),
        )
