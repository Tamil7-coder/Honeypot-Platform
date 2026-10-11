import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.attack import AttackSession, Command, File, Honeypot, LoginAttempt


class AttackRepository:
    """Persistence operations for honeypots, sessions, login attempts and commands."""

    def __init__(self, db: Session):
        self.db = db

    # --- Honeypots ---
    def get_or_create_honeypot(self, name: str, honeypot_type: str, host: str = "unknown") -> Honeypot:
        stmt = select(Honeypot).where(Honeypot.name == name)
        honeypot = self.db.execute(stmt).scalar_one_or_none()
        if honeypot:
            return honeypot
        honeypot = Honeypot(name=name, honeypot_type=honeypot_type, host=host)
        self.db.add(honeypot)
        self.db.commit()
        self.db.refresh(honeypot)
        return honeypot

    # --- Sessions ---
    def get_by_session_ref(self, session_ref: str) -> AttackSession | None:
        stmt = select(AttackSession).where(AttackSession.session_ref == session_ref)
        return self.db.execute(stmt).scalar_one_or_none()

    def update_risk_assessment(self, session: AttackSession, severity, risk_score: int) -> AttackSession:
        session.severity = severity
        session.risk_score = risk_score
        self.db.commit()
        self.db.refresh(session)
        return session

    def avg_risk_score_last_24h(self) -> dict:
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        stmt = select(func.avg(AttackSession.risk_score), func.count()).where(
            AttackSession.started_at >= since, AttackSession.risk_score.is_not(None)
        )
        row = self.db.execute(stmt).one()
        return {
            "avg_risk_score": round(row[0], 1) if row[0] is not None else None,
            "sample_size": row[1],
        }

    def create_session(self, session: AttackSession) -> AttackSession:
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def add_login_attempts(self, attempts: list[LoginAttempt]) -> None:
        self.db.add_all(attempts)
        self.db.commit()

    def add_commands(self, commands: list[Command]) -> None:
        self.db.add_all(commands)
        self.db.commit()

    def add_files(self, files: list[File]) -> None:
        self.db.add_all(files)
        self.db.commit()

    def get_session_detail(self, session_id: uuid.UUID) -> AttackSession | None:
        """Fetches a session with login_attempts/commands/files eager-loaded
        in a fixed number of queries (selectinload avoids N+1 round-trips
        the way a naive `.login_attempts` lazy-access would)."""
        stmt = (
            select(AttackSession)
            .options(
                selectinload(AttackSession.login_attempts),
                selectinload(AttackSession.commands),
                selectinload(AttackSession.files),
            )
            .where(AttackSession.id == session_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_sessions(
        self,
        skip: int = 0,
        limit: int = 50,
        source_ip: str | None = None,
        country_code: str | None = None,
        protocol: str | None = None,
        username: str | None = None,
        password: str | None = None,
        command: str | None = None,
        severity: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        session_ref: str | None = None,
    ) -> tuple[int, list[AttackSession]]:
        """
        Advanced Search (Phase 10, extended for multi-honeypot support).
        Filters are ANDed together; each is optional. Username/password/
        command require joining to login_attempts/commands (one-to-many
        with sessions), so DISTINCT is applied whenever either join is used
        to avoid duplicate rows when a session has multiple matching login
        attempts or commands.
        """
        stmt = select(AttackSession)
        needs_distinct = False

        if source_ip:
            # Partial match (cast INET to text) rather than exact equality —
            # "advanced search" implies typing a fragment like "192.168",
            # not always the full address.
            stmt = stmt.where(func.host(AttackSession.source_ip).ilike(f"%{source_ip}%"))

        if country_code:
            stmt = stmt.where(AttackSession.country_code == country_code.upper())

        if protocol:
            stmt = stmt.where(AttackSession.protocol == protocol.lower())

        if severity:
            stmt = stmt.where(AttackSession.severity == severity.lower())

        if date_from:
            stmt = stmt.where(AttackSession.started_at >= date_from)

        if date_to:
            stmt = stmt.where(AttackSession.started_at <= date_to)

        if session_ref:
            stmt = stmt.where(AttackSession.session_ref.ilike(f"%{session_ref}%"))

        if username or password:
            stmt = stmt.join(LoginAttempt, LoginAttempt.session_id == AttackSession.id)
            needs_distinct = True
            if username:
                stmt = stmt.where(LoginAttempt.username.ilike(f"%{username}%"))
            if password:
                stmt = stmt.where(LoginAttempt.password.ilike(f"%{password}%"))

        if command:
            stmt = stmt.join(Command, Command.session_id == AttackSession.id)
            needs_distinct = True
            stmt = stmt.where(Command.command_text.ilike(f"%{command}%"))

        if needs_distinct:
            stmt = stmt.distinct()

        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        stmt = stmt.order_by(AttackSession.started_at.desc()).offset(skip).limit(limit)
        items = list(self.db.execute(stmt).scalars().all())
        return total, items

    # --- Analytics aggregates ---
    def count_total_sessions(self) -> int:
        return self.db.execute(select(func.count()).select_from(AttackSession)).scalar_one()

    def count_active_sessions_since(self, since: datetime) -> int:
        stmt = select(func.count()).select_from(AttackSession).where(AttackSession.started_at >= since)
        return self.db.execute(stmt).scalar_one()

    def count_unique_attacker_ips(self) -> int:
        stmt = select(func.count(func.distinct(AttackSession.source_ip)))
        return self.db.execute(stmt).scalar_one()

    def top_attacker_ips(self, limit: int = 10) -> list[dict]:
        stmt = (
            select(AttackSession.source_ip, func.count().label("attack_count"))
            .group_by(AttackSession.source_ip)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [{"source_ip": str(row[0]), "attack_count": row[1]} for row in self.db.execute(stmt).all()]

    def top_targeted_services(self, limit: int = 10) -> list[dict]:
        stmt = (
            select(AttackSession.protocol, func.count().label("attack_count"))
            .group_by(AttackSession.protocol)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [{"protocol": row[0], "attack_count": row[1]} for row in self.db.execute(stmt).all()]

    def attacks_per_day(self, days: int = 7) -> list[dict]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        day_col = func.date_trunc("day", AttackSession.started_at)
        stmt = (
            select(day_col.label("day"), func.count().label("attack_count"))
            .where(AttackSession.started_at >= since)
            .group_by(day_col)
            .order_by(day_col)
        )
        return [{"day": row[0].date().isoformat(), "attack_count": row[1]} for row in self.db.execute(stmt).all()]

    def count_active_honeypots(self) -> int:
        stmt = select(func.count()).select_from(Honeypot).where(Honeypot.is_active.is_(True))
        return self.db.execute(stmt).scalar_one()

    def count_total_honeypots(self) -> int:
        return self.db.execute(select(func.count()).select_from(Honeypot)).scalar_one()

    def count_attacks_today(self) -> int:
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = select(func.count()).select_from(AttackSession).where(AttackSession.started_at >= start_of_day)
        return self.db.execute(stmt).scalar_one()

    def top_countries(self, limit: int = 10) -> list[dict]:
        stmt = (
            select(AttackSession.country_code, func.count().label("attack_count"))
            .where(AttackSession.country_code.is_not(None))
            .group_by(AttackSession.country_code)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [{"country_code": row[0], "attack_count": row[1]} for row in self.db.execute(stmt).all()]

    def top_usernames(self, limit: int = 10) -> list[dict]:
        stmt = (
            select(LoginAttempt.username, func.count().label("attempt_count"))
            .group_by(LoginAttempt.username)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [{"username": row[0], "attempt_count": row[1]} for row in self.db.execute(stmt).all()]

    def top_passwords(self, limit: int = 10) -> list[dict]:
        stmt = (
            select(LoginAttempt.password, func.count().label("attempt_count"))
            .group_by(LoginAttempt.password)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [{"password": row[0], "attempt_count": row[1]} for row in self.db.execute(stmt).all()]

    def honeypot_status(self) -> list[dict]:
        stmt = (
            select(
                Honeypot.name,
                Honeypot.honeypot_type,
                Honeypot.is_active,
                func.count(AttackSession.id).label("session_count"),
            )
            .outerjoin(AttackSession, AttackSession.honeypot_id == Honeypot.id)
            .group_by(Honeypot.id, Honeypot.name, Honeypot.honeypot_type, Honeypot.is_active)
            .order_by(Honeypot.name)
        )
        return [
            {"name": row[0], "type": row[1], "is_active": row[2], "session_count": row[3]}
            for row in self.db.execute(stmt).all()
        ]

    # --- Phase 5: Advanced Analytics ---

    def hourly_distribution(self) -> list[dict]:
        """Attack count grouped by hour-of-day (0-23), across all history."""
        hour_col = func.extract("hour", AttackSession.started_at)
        stmt = select(hour_col.label("hour"), func.count().label("attack_count")).group_by(hour_col).order_by(hour_col)
        counts = {int(row[0]): row[1] for row in self.db.execute(stmt).all()}
        return [{"hour": h, "attack_count": counts.get(h, 0)} for h in range(24)]

    def attack_heatmap(self) -> list[dict]:
        """Attack count grouped by (day_of_week, hour_of_day). dow: 0=Sunday..6=Saturday (Postgres convention)."""
        dow_col = func.extract("dow", AttackSession.started_at)
        hour_col = func.extract("hour", AttackSession.started_at)
        stmt = (
            select(dow_col.label("dow"), hour_col.label("hour"), func.count().label("attack_count"))
            .group_by(dow_col, hour_col)
        )
        return [
            {"day_of_week": int(row[0]), "hour": int(row[1]), "attack_count": row[2]}
            for row in self.db.execute(stmt).all()
        ]

    def weekly_trend(self, weeks: int = 8) -> list[dict]:
        since = datetime.now(timezone.utc) - timedelta(weeks=weeks)
        week_col = func.date_trunc("week", AttackSession.started_at)
        stmt = (
            select(week_col.label("week"), func.count().label("attack_count"))
            .where(AttackSession.started_at >= since)
            .group_by(week_col)
            .order_by(week_col)
        )
        return [{"week": row[0].date().isoformat(), "attack_count": row[1]} for row in self.db.execute(stmt).all()]

    def monthly_trend(self, months: int = 6) -> list[dict]:
        since = datetime.now(timezone.utc) - timedelta(days=months * 30)
        month_col = func.date_trunc("month", AttackSession.started_at)
        stmt = (
            select(month_col.label("month"), func.count().label("attack_count"))
            .where(AttackSession.started_at >= since)
            .group_by(month_col)
            .order_by(month_col)
        )
        return [{"month": row[0].date().isoformat(), "attack_count": row[1]} for row in self.db.execute(stmt).all()]

    def top_commands(self, limit: int = 10) -> list[dict]:
        stmt = (
            select(Command.command_text, func.count().label("execution_count"))
            .group_by(Command.command_text)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [{"command": row[0], "execution_count": row[1]} for row in self.db.execute(stmt).all()]

    def session_duration_stats(self) -> dict:
        stmt = select(
            func.avg(AttackSession.duration_seconds),
            func.min(AttackSession.duration_seconds),
            func.max(AttackSession.duration_seconds),
            func.percentile_cont(0.5).within_group(AttackSession.duration_seconds),
        ).where(AttackSession.duration_seconds.is_not(None))
        row = self.db.execute(stmt).one()
        return {
            "avg_seconds": round(row[0], 1) if row[0] is not None else None,
            "min_seconds": row[1],
            "max_seconds": row[2],
            "median_seconds": round(row[3], 1) if row[3] is not None else None,
        }

    def risk_distribution(self) -> list[dict]:
        stmt = select(AttackSession.severity, func.count().label("attack_count")).group_by(AttackSession.severity)
        return [
            {"severity": row[0].value if row[0] else "unclassified", "attack_count": row[1]}
            for row in self.db.execute(stmt).all()
        ]

    # --- Phase 9: Reports (date-range scoped, kept separate from the
    # all-time dashboard/analytics queries above so those can't regress) ---

    @staticmethod
    def _in_range(since: datetime, until: datetime):
        return AttackSession.started_at.between(since, until)

    def report_summary(self, since: datetime, until: datetime) -> dict:
        stmt = select(
            func.count(),
            func.count(func.distinct(AttackSession.source_ip)),
        ).where(self._in_range(since, until))
        total, unique_ips = self.db.execute(stmt).one()
        return {"total_attacks": total, "unique_attacker_ips": unique_ips}

    def report_severity_breakdown(self, since: datetime, until: datetime) -> list[dict]:
        stmt = (
            select(AttackSession.severity, func.count())
            .where(self._in_range(since, until))
            .group_by(AttackSession.severity)
            .order_by(func.count().desc())
        )
        return [
            {"severity": row[0].value if row[0] else "unclassified", "attack_count": row[1]}
            for row in self.db.execute(stmt).all()
        ]

    def report_top_attacker_ips(self, since: datetime, until: datetime, limit: int = 15) -> list[dict]:
        stmt = (
            select(AttackSession.source_ip, func.count().label("attack_count"))
            .where(self._in_range(since, until))
            .group_by(AttackSession.source_ip)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [{"source_ip": str(row[0]), "attack_count": row[1]} for row in self.db.execute(stmt).all()]

    def report_top_countries(self, since: datetime, until: datetime, limit: int = 10) -> list[dict]:
        stmt = (
            select(AttackSession.country_code, func.count().label("attack_count"))
            .where(self._in_range(since, until), AttackSession.country_code.is_not(None))
            .group_by(AttackSession.country_code)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [{"country_code": row[0], "attack_count": row[1]} for row in self.db.execute(stmt).all()]

    def report_top_credentials(self, since: datetime, until: datetime, limit: int = 10) -> list[dict]:
        stmt = (
            select(LoginAttempt.username, LoginAttempt.password, func.count().label("attempt_count"))
            .join(AttackSession, AttackSession.id == LoginAttempt.session_id)
            .where(self._in_range(since, until))
            .group_by(LoginAttempt.username, LoginAttempt.password)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [
            {"username": row[0], "password": row[1], "attempt_count": row[2]} for row in self.db.execute(stmt).all()
        ]

    def report_sessions(self, since: datetime, until: datetime, limit: int = 500) -> list[AttackSession]:
        stmt = (
            select(AttackSession)
            .where(self._in_range(since, until))
            .order_by(AttackSession.risk_score.desc().nulls_last(), AttackSession.started_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    # --- Phase 12: Retention Policy ---

    def purge_sessions_older_than(self, days: int) -> int:
        """Deletes sessions older than `days`, along with their
        login_attempts/commands/files/alerts (via the ORM relationship
        cascades on AttackSession, not a raw bulk DELETE -- the child tables'
        foreign keys aren't DB-level ON DELETE CASCADE, so this must go
        through session.delete() per row to cascade correctly)."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = select(AttackSession).where(AttackSession.started_at < cutoff)
        old_sessions = list(self.db.execute(stmt).scalars().all())
        for session in old_sessions:
            self.db.delete(session)
        self.db.commit()
        return len(old_sessions)
