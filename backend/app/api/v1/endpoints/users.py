import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import RoleName, User
from app.schemas.user import UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["User Management"])


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        is_active=user.is_active,
        is_email_verified=user.is_email_verified,
        role=user.role.name,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return _to_response(current_user)


@router.get("", response_model=list[UserResponse], dependencies=[Depends(require_roles(RoleName.ADMIN))])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    service = UserService(db)
    return [_to_response(u) for u in service.list_users(skip=skip, limit=limit)]


@router.patch(
    "/{user_id}/deactivate", response_model=UserResponse, dependencies=[Depends(require_roles(RoleName.ADMIN))]
)
def deactivate_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    service = UserService(db)
    return _to_response(service.deactivate_user(user_id))


@router.patch(
    "/{user_id}/activate", response_model=UserResponse, dependencies=[Depends(require_roles(RoleName.ADMIN))]
)
def activate_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    service = UserService(db)
    return _to_response(service.activate_user(user_id))
