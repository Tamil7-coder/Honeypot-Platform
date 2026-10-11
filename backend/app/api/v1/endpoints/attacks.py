import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.attack import AttackReplayResponse, AttackSessionIngest, AttackSessionListResponse, AttackSessionResponse
from app.services.alert_service import AlertService
from app.services.attack_service import AttackService
from app.services.connection_manager import connection_manager
from app.repositories.settings_repository import SettingsRepository

router = APIRouter(prefix="/attacks", tags=["Attack Monitoring"])


@router.post("/ingest", response_model=AttackSessionResponse, status_code=201)
async def ingest_attack_session(
    payload: AttackSessionIngest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """
    Ingestion endpoint called by honeypot log-shippers.

    Every ingested session is broadcast live to connected WebSocket clients
    (Phase 4) so the dashboard updates without polling. If the session's
    computed severity meets the configured alert threshold, an alert is also
    created and an email dispatched in the background (Phase 3) so ingestion
    latency is unaffected by SMTP round-trips or failures.

    NOTE: In production this endpoint should be protected by a dedicated
    service-to-service API key (separate from user JWTs) rather than being
    open — wired up in Module 2 alongside the shipper adapters.
    """
    service = AttackService(db)
    session = service.ingest_session(payload)

    await connection_manager.broadcast(
        {
            "type": "new_attack",
            "data": {
                "id": str(session.id),
                "source_ip": str(session.source_ip),
                "protocol": session.protocol,
                "country_code": session.country_code,
                "severity": session.severity.value if session.severity else None,
                "started_at": session.started_at.isoformat(),
            },
        }
    )

    min_severity = SettingsRepository(db).get().alert_min_severity
    if AlertService.should_alert(session.severity, min_severity):
        background_tasks.add_task(AlertService().create_and_send_alert, session.id)

    return AttackSessionResponse.model_validate(session)


@router.get("", response_model=AttackSessionListResponse, dependencies=[Depends(get_current_user)])
def list_attack_sessions(
    skip: int = 0,
    limit: int = Query(50, le=200),
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
    db: Session = Depends(get_db),
):
    """
    Advanced Search: all filters are optional and ANDed together.
    - source_ip / session_ref: partial match
    - country_code / protocol / severity: exact match (case-insensitive)
    - username / password / command: partial match, searched across all
      login attempts / commands in each session
    - date_from / date_to: filters on session start time
    """
    service = AttackService(db)
    return service.list_sessions(
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


@router.get(
    "/{session_id}/replay", response_model=AttackReplayResponse, dependencies=[Depends(get_current_user)]
)
def get_attack_replay(session_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Phase 8: returns the full chronological timeline for a session —
    login attempts, commands, and file transfers merged in order, plus a
    disconnect marker — for the Attack Replay page.
    """
    service = AttackService(db)
    return service.get_replay(session_id)
