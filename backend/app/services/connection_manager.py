"""
In-memory WebSocket connection registry for the live dashboard feed.

Single-process design: connections are held in a Python list on this
process. This is correct for a single backend instance (this deployment).
If the platform is later horizontally scaled across multiple backend
processes/replicas, broadcasts would need to go through a shared pub/sub
layer (e.g. Redis) instead of this in-memory list so every replica's
connected clients receive events regardless of which replica handled the
originating request — noted here rather than built, since that scale
doesn't exist yet.
"""
import asyncio
import json

from fastapi import WebSocket

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Called once at app startup so background-thread code can safely
        schedule broadcasts onto the event loop via run_coroutine_threadsafe."""
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)
        logger.info("WebSocket connected (total=%d)", len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)
        logger.info("WebSocket disconnected (total=%d)", len(self._connections))

    async def broadcast(self, message: dict) -> None:
        """Send `message` (JSON-serialized) to every connected client.
        Dead connections are pruned rather than raising."""
        if not self._connections:
            return
        payload = json.dumps(message, default=str)
        dead: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_text(payload)
            except Exception:  # noqa: BLE001 - a broken connection shouldn't stop the rest
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)

    def broadcast_sync(self, message: dict) -> None:
        """Thread-safe broadcast for callers running outside the event loop
        (e.g. AlertService, which runs in a threadpool because it does
        blocking SMTP I/O)."""
        if self._loop is None:
            logger.warning("broadcast_sync called before event loop was bound; dropping message")
            return
        asyncio.run_coroutine_threadsafe(self.broadcast(message), self._loop)


connection_manager = ConnectionManager()
