import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.repositories.user_repository import UserRepository
from app.services.connection_manager import connection_manager

router = APIRouter(tags=["Real-Time"])


def _authenticate_ws_token(token: str, db: Session) -> bool:
    """WebSocket handshakes can't carry Authorization headers from a browser,
    so the access token is passed as a query param instead. Same validation
    rules as the HTTP path (get_current_user) — access-type token, active user."""
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        return False
    try:
        user_id = uuid.UUID(payload.get("sub"))
    except (ValueError, TypeError):
        return False

    user = UserRepository(db).get_by_id(user_id)
    return user is not None and user.is_active


@router.websocket("/ws/live")
async def live_feed(websocket: WebSocket, token: str = ""):
    db = SessionLocal()
    try:
        if not token or not _authenticate_ws_token(token, db):
            await websocket.close(code=4401)  # custom close code: unauthorized
            return
    finally:
        db.close()

    await connection_manager.connect(websocket)
    try:
        while True:
            # Clients don't send anything meaningful; awaiting receive is how
            # we detect disconnects (WebSocketDisconnect is raised on close).
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(websocket)
