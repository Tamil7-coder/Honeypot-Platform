"""
Security primitives: password hashing and JWT token issuance/verification.

Kept isolated from business logic so algorithms/policies can change without
touching services or API routes (Single Responsibility Principle).
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str, extra_claims: dict[str, Any] | None = None, expire_minutes: int | None = None
) -> str:
    return _create_token(
        subject,
        expires_delta=timedelta(minutes=expire_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
        extra_claims=extra_claims,
    )


def create_refresh_token(subject: str, remember_me: bool = False) -> str:
    expire_minutes = (
        settings.REMEMBER_ME_REFRESH_TOKEN_EXPIRE_MINUTES if remember_me else settings.REFRESH_TOKEN_EXPIRE_MINUTES
    )
    return _create_token(
        subject,
        expires_delta=timedelta(minutes=expire_minutes),
        token_type="refresh",
    )


def create_password_reset_token(subject: str) -> str:
    return _create_token(
        subject,
        expires_delta=timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
        token_type="password_reset",
    )


def create_email_verification_token(subject: str) -> str:
    return _create_token(
        subject,
        expires_delta=timedelta(minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES),
        token_type="email_verification",
    )


def _create_token(
    subject: str,
    expires_delta: timedelta,
    token_type: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "type": token_type,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
