import uuid
from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import RoleName, User
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise credentials_exception

    try:
        user_id = uuid.UUID(payload.get("sub"))
    except (ValueError, TypeError):
        raise credentials_exception

    user = UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def require_roles(*allowed_roles: RoleName):
    """Dependency factory for RBAC-protected endpoints.

    Usage: Depends(require_roles(RoleName.ADMIN))
    """

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return checker
