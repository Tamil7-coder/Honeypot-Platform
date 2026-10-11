from fastapi import APIRouter

from app.api.v1.endpoints import analytics, attacks, auth, health, notifications, reports, settings, threat_intel, users, ws

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(attacks.router)
api_router.include_router(analytics.router)
api_router.include_router(threat_intel.router)
api_router.include_router(reports.router)
api_router.include_router(notifications.router)
api_router.include_router(settings.router)
api_router.include_router(ws.router)
