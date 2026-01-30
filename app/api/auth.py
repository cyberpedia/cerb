"""
Authentication API Endpoints for Cerberus CTF Platform.

Handles user registration, login, logout, and session management.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import (
    AdminUser,
    CurrentUser,
    DbSession,
    get_current_user,
    get_db_session,
)
from app.models.user import User
from app.services.auth_service import (
    AuthError,
    authenticate_user,
    create_access_token,
    create_session,
    get_password_hash,
    invalidate_session,
    register_user,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


# ============== Request/Response Models ==============

class RegisterRequest(BaseModel):
    """User registration request."""

    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(..., min_length=8)
    invite_code: str | None = Field(None, description="Required for invite-only mode")
    accepted_tos: bool = Field(..., description="Must accept Terms of Service")

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "hacker123",
                "email": "user@example.com",
                "password": "securepassword123",
                "invite_code": "optional-invite-code",
                "accepted_tos": True,
            }
        }
    }


class LoginRequest(BaseModel):
    """User login request."""

    username_or_email: str = Field(..., description="Username or email address")
    password: str = Field(..., description="Password")

    model_config = {
        "json_schema_extra": {
            "example": {
                "username_or_email": "hacker123",
                "password": "securepassword123",
            }
        }
    }


class TokenResponse(BaseModel):
    """Token response for API clients."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """User data response."""

    id: str
    username: str
    email: str
    role: str
    is_verified: bool
    team_id: str | None
    oauth_provider: str

    @classmethod
    def from_user(cls, user: User) -> "UserResponse":
        return cls(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=user.role,
            is_verified=user.is_verified,
            team_id=str(user.team_id) if user.team_id else None,
            oauth_provider=user.oauth_provider,
        )


class AuthResponse(BaseModel):
    """Authentication response with user data and tokens."""

    user: UserResponse
    access_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None


class RegistrationStatusResponse(BaseModel):
    """Registration status and requirements."""

    is_open: bool
    mode: str
    requires_invite: bool
    requires_email_domain: bool
    allowed_domains: list[str] | None = None


# ============== Endpoints ==============

@router.get("/registration-status", response_model=RegistrationStatusResponse)
async def get_registration_status(session: DbSession) -> RegistrationStatusResponse:
    """
    Get current registration status and requirements.

    This endpoint is public and helps clients understand
    what is required for registration.
    """
    from app.models.system_settings import SystemSettings

    system_settings = await SystemSettings.get(session)

    allowed_domains = None
    if system_settings.allowed_email_domains:
        allowed_domains = [
            d.strip()
            for d in system_settings.allowed_email_domains.split(",")
            if d.strip()
        ]

    return RegistrationStatusResponse(
        is_open=system_settings.is_registration_open,
        mode=system_settings.registration_mode,
        requires_invite=system_settings.registration_mode == "invite",
        requires_email_domain=system_settings.registration_mode == "email_restricted",
        allowed_domains=allowed_domains,
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: Request,
    response: Response,
    data: RegisterRequest,
    session: DbSession,
) -> AuthResponse:
    """
    Register a new user account.

    Registration requirements depend on system settings:
    - **public**: Open registration, no restrictions
    - **email_restricted**: Email must match allowed domains
    - **invite**: Valid invite code required

    On success, creates a session cookie for browser clients.
    """
    if not data.accepted_tos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must accept the Terms of Service",
        )

    try:
        user = await register_user(
            session=session,
            username=data.username,
            email=data.email,
            password=data.password,
            invite_code=data.invite_code,
            accepted_tos=data.accepted_tos,
        )
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    # Create session for the new user
    session_id = await create_session(
        user_id=str(user.id),
        request=request,
        paranoid_mode=True,
    )

    # Set session cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=not settings.debug,  # Secure in production
        samesite="lax",
        max_age=60 * 60 * 24 * settings.refresh_token_expire_days,  # days in seconds
    )

    # Create access token for API clients
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    return AuthResponse(
        user=UserResponse.from_user(user),
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: Request,
    response: Response,
    data: LoginRequest,
    session: DbSession,
) -> AuthResponse:
    """
    Authenticate and create a session.

    Accepts username or email with password.
    On success, creates a session cookie for browser clients
    and returns an access token for API clients.
    """
    try:
        user = await authenticate_user(
            session=session,
            username_or_email=data.username_or_email,
            password=data.password,
        )
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    # Create session
    session_id = await create_session(
        user_id=str(user.id),
        request=request,
        paranoid_mode=True,
    )

    # Set session cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        max_age=60 * 60 * 24 * settings.refresh_token_expire_days,
    )

    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    return AuthResponse(
        user=UserResponse.from_user(user),
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout")
async def logout(
    response: Response,
    session_cookie: Annotated[str | None, Cookie(alias="session_id")] = None,
) -> dict[str, str]:
    """
    Logout and invalidate the current session.

    Clears the session cookie and invalidates the session in Redis.
    """
    if session_cookie:
        await invalidate_session(session_cookie)

    # Clear cookie
    response.delete_cookie(key="session_id")

    return {"message": "Successfully logged out"}


@router.post("/logout-all")
async def logout_all(
    response: Response,
    user: CurrentUser,
) -> dict[str, str]:
    """
    Logout from all devices.

    Invalidates all sessions for the current user.
    Requires authentication.
    """
    from app.services.auth_service import invalidate_all_user_sessions

    await invalidate_all_user_sessions(str(user.id))

    # Clear current cookie
    response.delete_cookie(key="session_id")

    return {"message": "Successfully logged out from all devices"}


@router.get("/me", response_model=UserResponse)
async def get_me(user: CurrentUser) -> UserResponse:
    """
    Get the current authenticated user's information.
    """
    return UserResponse.from_user(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(user: CurrentUser) -> TokenResponse:
    """
    Refresh the access token.

    Returns a new access token with extended expiration.
    Requires a valid session.
    """
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    user: CurrentUser,
    session: DbSession,
    response: Response,
) -> dict[str, str]:
    """
    Change the current user's password.

    Requires the current password for verification.
    Invalidates all existing sessions after password change.
    """
    from app.services.auth_service import invalidate_all_user_sessions

    # Verify current password
    if not user.password_hash or not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password length
    if len(new_password) < settings.password_min_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at least {settings.password_min_length} characters",
        )

    # Update password
    user.password_hash = get_password_hash(new_password)
    await session.commit()

    # Invalidate all sessions (security best practice)
    await invalidate_all_user_sessions(str(user.id))

    # Clear current cookie
    response.delete_cookie(key="session_id")

    return {"message": "Password changed successfully. Please log in again."}


# ============== Admin Endpoints ==============

@router.post("/admin/create-invite")
async def create_invite_code(
    uses: int = Field(1, ge=1, le=100),
    admin_user: AdminUser = None,
) -> dict[str, str]:
    """
    Create an invite code for invite-only registration.

    Admin only endpoint.
    """
    import secrets

    from app.services.auth_service import get_redis

    invite_code = secrets.token_urlsafe(16)
    redis_client = await get_redis()

    await redis_client.hset(
        f"invite:{invite_code}",
        mapping={
            "uses_remaining": uses,
            "created_by": str(admin_user.id),
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {
        "invite_code": invite_code,
        "uses": uses,
        "message": "Invite code created successfully",
    }


