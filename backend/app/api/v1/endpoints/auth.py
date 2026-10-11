from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _to_user_response(user: User) -> UserResponse:
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


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("10/minute")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    user = service.register(payload)
    return _to_user_response(user)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    user = service.authenticate(payload.email, payload.password)
    return service.issue_tokens(user, remember_me=payload.remember_me)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
def refresh(request: Request, payload: RefreshRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.refresh_access_token(payload.refresh_token)


@router.post("/forgot-password", status_code=202)
@limiter.limit("5/minute")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Always responds 202 regardless of whether the email exists, to avoid
    leaking account existence. Real delivery arrives with Phase 3 (SMTP);
    until then, in development mode only, the token is echoed back so the
    reset flow can be tested end-to-end.
    """
    service = AuthService(db)
    token = service.request_password_reset(payload.email)

    response: dict = {"detail": "If that email is registered, a reset link has been sent."}
    if settings.ENVIRONMENT == "development" and token:
        response["dev_reset_token"] = token
    return response


@router.post("/reset-password", response_model=UserResponse)
@limiter.limit("10/minute")
def reset_password(request: Request, payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    user = service.reset_password(payload.token, payload.new_password)
    return _to_user_response(user)


@router.post("/change-password", response_model=UserResponse)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AuthService(db)
    user = service.change_password(current_user, payload.current_password, payload.new_password)
    return _to_user_response(user)


@router.post("/request-email-verification", status_code=202)
def request_email_verification(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = AuthService(db)
    token = service.request_email_verification(current_user)

    response: dict = {"detail": "Verification email requested."}
    if settings.ENVIRONMENT == "development":
        response["dev_verification_token"] = token
    return response


@router.post("/verify-email", response_model=UserResponse)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    user = service.verify_email(payload.token)
    return _to_user_response(user)
