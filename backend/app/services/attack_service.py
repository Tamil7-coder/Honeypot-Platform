import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging_config import get_logger
from app.models.attack import AttackSession, Command, File, LoginAttempt
from app.repositories.attack_repository import AttackRepository
from app.schemas.attack import (
    AttackReplayResponse,
    AttackSessionIngest,
    AttackSessionListResponse,
    AttackSessionResponse,
    ReplayEvent,
)
from app.services.risk_scoring_service import compute_risk_score

logger = get_logger(__name__)


class AttackService:
    """Business logic for ingesting and querying honeypot attack sessions.

    This is the single entry point every honeypot log-shipper adapter
    (Cowrie, OpenCanary, Dionaea) must call, guaranteeing a consistent
    storage model regardless of the source honeypot's native log format.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = AttackRepository(db)

    def ingest_session(self, payload: AttackSessionIngest) -> AttackSession:
        existing = self.repo.get_by_session_ref(payload.session_ref)
        if existing is not None:
            logger.info("Duplicate session ingest ignored: %s", payload.session_ref)
            return existing

        honeypot = self.repo.get_or_create_honeypot(
            name=payload.honeypot_name,
            honeypot_type=payload.protocol,
        )

        duration = None
        if payload.ended_at:
            duration = int((payload.ended_at - payload.started_at).total_seconds())

        session = AttackSession(
            honeypot_id=honeypot.id,
            session_ref=payload.session_ref,
            source_ip=str(payload.source_ip),
            source_port=payload.source_port,
            destination_port=payload.destination_port,
            protocol=payload.protocol,
            country_code=payload.country_code,
            started_at=payload.started_at,
            ended_at=payload.ended_at,
            duration_seconds=duration,
        )
        session = self.repo.create_session(session)

        if payload.login_attempts:
            attempts = [
                LoginAttempt(
                    session_id=session.id,
                    username=a.username,
                    password=a.password,
                    success=a.success,
                )
                for a in payload.login_attempts
            ]
            self.repo.add_login_attempts(attempts)

        if payload.commands:
            commands = [
                Command(session_id=session.id, command_text=c.command_text, command_metadata=c.command_metadata)
                for c in payload.commands
            ]
            self.repo.add_commands(commands)

        if payload.files:
            files = [
                File(
                    session_id=session.id,
                    direction=f.direction,
                    url=f.url,
                    filename=f.filename,
                    file_size=f.file_size,
                    sha256=f.sha256,
                )
                for f in payload.files
            ]
            self.repo.add_files(files)

        distinct_passwords = {a.password for a in payload.login_attempts}
        assessment = compute_risk_score(
            protocol=payload.protocol,
            login_success=any(a.success for a in payload.login_attempts),
            failed_login_count=sum(1 for a in payload.login_attempts if not a.success),
            distinct_password_count=len(distinct_passwords),
            command_texts=[c.command_text for c in payload.commands],
            file_count=len(payload.files),
        )
        session = self.repo.update_risk_assessment(session, assessment.severity, assessment.score)

        logger.info(
            "Ingested attack session %s from %s via %s (risk_score=%d, severity=%s)",
            session.session_ref,
            session.source_ip,
            session.protocol,
            assessment.score,
            assessment.severity.value,
        )
        return session

    def list_sessions(
        self,
        skip: int,
        limit: int,
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
    ) -> AttackSessionListResponse:
        total, items = self.repo.list_sessions(
            skip=skip,
            limit=limit,
            source_ip=source_ip,
            country_code=country_code,
            protocol=protocol,
            username=username,
            password=password,
            command=command,
            severity=severity,
            date_from=date_from,
            date_to=date_to,
            session_ref=session_ref,
        )
        return AttackSessionListResponse(
            total=total,
            items=[AttackSessionResponse.model_validate(i) for i in items],
        )

    def get_replay(self, session_id: uuid.UUID) -> AttackReplayResponse:
        """Builds the Phase 8 replay timeline: every login attempt, command,
        and file transfer merged into a single chronologically-sorted
        sequence, plus a synthetic 'disconnect' event if the session has
        ended. Login/command/file rows don't share a table, so this can't be
        done with a single ORDER BY — it's assembled in Python instead."""
        session = self.repo.get_session_detail(session_id)
        if session is None:
            raise NotFoundError("Attack session not found")

        events: list[ReplayEvent] = []

        for attempt in session.login_attempts:
            events.append(
                ReplayEvent(
                    event_type="login_success" if attempt.success else "login_failed",
                    timestamp=attempt.attempted_at,
                    detail={"username": attempt.username, "password": attempt.password},
                )
            )

        for command in session.commands:
            events.append(
                ReplayEvent(
                    event_type="command",
                    timestamp=command.executed_at,
                    detail={"command_text": command.command_text, "metadata": command.command_metadata},
                )
            )

        for file in session.files:
            events.append(
                ReplayEvent(
                    event_type=file.direction.value,
                    timestamp=file.occurred_at,
                    detail={
                        "filename": file.filename,
                        "url": file.url,
                        "file_size": file.file_size,
                        "sha256": file.sha256,
                    },
                )
            )

        events.sort(key=lambda e: e.timestamp)

        if session.ended_at:
            events.append(
                ReplayEvent(
                    event_type="disconnect",
                    timestamp=session.ended_at,
                    detail={"duration_seconds": session.duration_seconds},
                )
            )

        return AttackReplayResponse(
            session=AttackSessionResponse.model_validate(session),
            timeline=events,
        )
