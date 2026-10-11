import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidOrExpiredTokenError,
    UserAlreadyExistsError,
    UserInactiveError,
)
from app.core.logging_config import get_logger
from app.core.security import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import RoleName, User
from app.repositories.settings_repository import SettingsRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, TokenResponse

logger = get_logger(__name__)


class AuthService:
    """Business logic for authentication: registration, login, token refresh,
    password reset, password change, and email verification.

    Login is email-based (Phase 2). `username` is retained on the User model
    for backward compatibility with existing data/audit trails and is
    auto-derived from the email's local-part at registration time, so no
    caller needs to supply or think about it anymore.
    """

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.settings_repo = SettingsRepository(db)

    def register(self, payload: RegisterRequest) -> User:
        if self.user_repo.get_by_email(payload.email):
            raise UserAlreadyExistsError()

        role = self.user_repo.get_role_by_name(RoleName.VIEWER)
        if role is None:
            raise RuntimeError("Default role 'viewer' is not seeded in the database")

        user = User(
            username=self._generate_unique_username(payload.email),
            full_name=payload.full_name,
            email=payload.email,
            hashed_password=hash_password(payload.password),
            role_id=role.id,
        )
        user = self.user_repo.create(user)
        logger.info("New user registered: %s (%s)", user.email, user.username)
        return user

    def authenticate(self, email: str, password: str) -> User:
        user = self.user_repo.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            logger.warning("Failed login attempt for email=%s", email)
            raise InvalidCredentialsError()
        if not user.is_active:
            raise UserInactiveError()

        user.last_login_at = datetime.now(timezone.utc)
        self.user_repo.update(user)
        logger.info("User authenticated: %s", user.email)
        return user

    def issue_tokens(self, user: User, remember_me: bool = False) -> TokenResponse:
        session_timeout = self.settings_repo.get().session_timeout_minutes
        access_token = create_access_token(
            str(user.id), extra_claims={"role": user.role.name.value}, expire_minutes=session_timeout
        )
        refresh_token = create_refresh_token(str(user.id), remember_me=remember_me)
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token)
        if payload is None or payload.get("type") != "refresh":
            raise InvalidCredentialsError()

        user = self._get_user_from_subject(payload)
        if user is None or not user.is_active:
            raise InvalidCredentialsError()

        return self.issue_tokens(user)

    # --- Password reset ---

    def request_password_reset(self, email: str) -> str | None:
        """Returns the reset token if the account exists, else None.

        Always returns without error either way at the API layer (to avoid
        leaking which emails are registered) — the service layer surfaces
        the None/token distinction only for internal logging/delivery.
        """
        user = self.user_repo.get_by_email(email)
        if user is None:
            logger.info("Password reset requested for unknown email=%s (no-op)", email)
            return None

        token = create_password_reset_token(str(user.id))
        logger.info("Password reset token issued for user=%s", user.email)
        return token

    def reset_password(self, token: str, new_password: str) -> User:
        payload = decode_token(token)
        if payload is None or payload.get("type") != "password_reset":
            raise InvalidOrExpiredTokenError()

        user = self._get_user_from_subject(payload)
        if user is None:
            raise InvalidOrExpiredTokenError()

        user.hashed_password = hash_password(new_password)
        self.user_repo.update(user)
        logger.info("Password reset completed for user=%s", user.email)
        return user

    def change_password(self, user: User, current_password: str, new_password: str) -> User:
        if not verify_password(current_password, user.hashed_password):
            raise InvalidCredentialsError()

        user.hashed_password = hash_password(new_password)
        self.user_repo.update(user)
        logger.info("Password changed for user=%s", user.email)
        return user

    # --- Email verification (optional, non-blocking) ---

    def request_email_verification(self, user: User) -> str:
        token = create_email_verification_token(str(user.id))
        logger.info("Email verification token issued for user=%s", user.email)
        return token

    def verify_email(self, token: str) -> User:
        payload = decode_token(token)
        if payload is None or payload.get("type") != "email_verification":
            raise InvalidOrExpiredTokenError()

        user = self._get_user_from_subject(payload)
        if user is None:
            raise InvalidOrExpiredTokenError()

        user.is_email_verified = True
        self.user_repo.update(user)
        logger.info("Email verified for user=%s", user.email)
        return user

    # --- Internal helpers ---

    def _get_user_from_subject(self, payload: dict) -> User | None:
        try:
            user_id = uuid.UUID(payload["sub"])
        except (ValueError, KeyError, TypeError):
            return None
        return self.user_repo.get_by_id(user_id)

    def _generate_unique_username(self, email: str) -> str:
        base = re.sub(r"[^a-zA-Z0-9_]", "", email.split("@")[0]).lower() or "user"
        base = base[:56]  # leave room for numeric suffixes within the 64-char column
        candidate = base
        suffix = 1
        while self.user_repo.username_exists(candidate):
            candidate = f"{base}{suffix}"
            suffix += 1
        return candidate
