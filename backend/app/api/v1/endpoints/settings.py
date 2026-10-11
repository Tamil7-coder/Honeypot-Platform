from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import RoleName
from app.schemas.settings import (
    RetentionCleanupResponse,
    SettingsResponse,
    SettingsUpdateRequest,
    TestEmailRequest,
    TestEmailResponse,
)
from app.services.settings_service import SettingsService

router = APIRouter(
    prefix="/settings", tags=["Settings"], dependencies=[Depends(require_roles(RoleName.ADMIN))]
)


@router.get("", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    return SettingsService(db).get_settings()


@router.patch("", response_model=SettingsResponse)
def update_settings(payload: SettingsUpdateRequest, db: Session = Depends(get_db)):
    return SettingsService(db).update_settings(payload)


@router.post("/run-retention-cleanup", response_model=RetentionCleanupResponse)
def run_retention_cleanup(db: Session = Depends(get_db)):
    return SettingsService(db).run_retention_cleanup()


@router.post("/test-email", response_model=TestEmailResponse)
def send_test_email(payload: TestEmailRequest, db: Session = Depends(get_db)):
    return SettingsService(db).send_test_email(payload.to_email)
