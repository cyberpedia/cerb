"""
Authentication Service for Cerberus CTF Platform.

Handles user registration, authentication, and session management
with support for multiple registration modes and paranoid session security.
"""

import hashlib
import hmac
import ipaddress
import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import redis.asyncio as redis
from fastapi import HTTPException, Request, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.system_settings import SystemSettings
from app.models.user import User

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Redis connection for session storage
_redis_pool: redis.Redis | None = None


class RegistrationMode(str, Enum):
    """Registration mode options."""

    PUBLIC = "public"
    INVITE = "invite"
    EMAIL_RESTRICTED = "email_restricted"


class EventState(str, Enum):
    """CTF Event state."""

    PRE_EVENT = "pre_event"
    RUNNING = "running"
    FROZEN = "frozen"
    ENDED = "ended"


class AuthError(Exception):
    """Custom authentication error."""

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


async def get_redis() -> redis.Redis:
    """Get or create Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        # Use Redis URL from environment or default
        redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")
        _redis_pool = redis.from_url(redis_url, decode_responses=True)
    return _redis_pool


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a plain password."""
    return pwd_context.hash(password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError as e:
        raise AuthError("Invalid or expired token", status.HTTP_401_UNAUTHORIZED) from e


def _get_ip_subnet(ip: str) -> str:
    """Extract /24 subnet from IP address for session binding."""
    try:
        ip_obj = ipaddress.ip_address(ip)
        if isinstance(ip_obj, ipaddress.IPv4Address):
            # For IPv4, return /24 subnet (first 3 octets)
            return str(ipaddress.ip_network(f"{ip}/24", strict=False).network_address)
        else:
            # For IPv6, return /64 subnet
            return str(ipaddress.ip_network(f"{ip}/64", strict=False).network_address)
    except ValueError:
        return ip


def _get_client_fingerprint(request: Request) -> tuple[str, str]:
    """Extract User-Agent and IP subnet from request for session binding."""
    user_agent = request.headers.get("user-agent", "")
    client_ip = request.client.host if request.client else "unknown"
    ip_subnet = _get_ip_subnet(client_ip)
    return user_agent, ip_subnet


def _hash_fingerprint(user_agent: str, ip_subnet: str) -> str:
    """Create a hash of the fingerprint for secure storage."""
    fingerprint = f"{user_agent}:{ip_subnet}"
    return hashlib.sha256(fingerprint.encode()).hexdigest()


async def create_session(
    user_id: str,
    request: Request,
    paranoid_mode: bool = True,
) -> str:
    """
    Create a new session with optional paranoid mode binding.

    Args:
        user_id: The user's UUID as string
        request: FastAPI request object
        paranoid_mode: If True, bind session to User-Agent and IP subnet

    Returns:
        Session ID string
    """
    session_id = secrets.token_urlsafe(32)
    redis_client = await get_redis()

    session_data = {
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if paranoid_mode:
        user_agent, ip_subnet = _get_client_fingerprint(request)
        fingerprint_hash = _hash_fingerprint(user_agent, ip_subnet)
        session_data["fingerprint"] = fingerprint_hash

    # Store session in Redis with expiration
    session_key = f"session:{session_id}"
    await redis_client.hset(session_key, mapping=session_data)
    await redis_client.expire(
        session_key,
        timedelta(days=settings.refresh_token_expire_days),
    )

    return session_id


async def validate_session(
    session_id: str,
    request: Request,
    paranoid_mode: bool = True,
) -> str:
    """
    Validate a session and check fingerprint in paranoid mode.

    Args:
        session_id: The session ID to validate
        request: FastAPI request object
        paranoid_mode: If True, validate fingerprint binding

    Returns:
        User ID if session is valid

    Raises:
        AuthError: If session is invalid or fingerprint mismatch
    """
    redis_client = await get_redis()
    session_key = f"session:{session_id}"

    session_data = await redis_client.hgetall(session_key)
    if not session_data:
        raise AuthError("Invalid or expired session", status.HTTP_401_UNAUTHORIZED)

    # Check fingerprint in paranoid mode
    if paranoid_mode and "fingerprint" in session_data:
        user_agent, ip_subnet = _get_client_fingerprint(request)
        current_fingerprint = _hash_fingerprint(user_agent, ip_subnet)
        stored_fingerprint = session_data.get("fingerprint")

        if not hmac.compare_digest(current_fingerprint, stored_fingerprint):
            # Potential cookie hijacking - invalidate session
            await redis_client.delete(session_key)
            raise AuthError(
                "Session invalidated due to suspicious activity",
                status.HTTP_401_UNAUTHORIZED,
            )

    # Refresh session expiration on valid use
    await redis_client.expire(
        session_key,
        timedelta(days=settings.refresh_token_expire_days),
    )

    return session_data["user_id"]


async def invalidate_session(session_id: str) -> None:
    """Invalidate a session by deleting it from Redis."""
    redis_client = await get_redis()
    await redis_client.delete(f"session:{session_id}")


async def invalidate_all_user_sessions(user_id: str) -> None:
    """Invalidate all sessions for a user (e.g., on password change)."""
    redis_client = await get_redis()
    # This requires a secondary index or scanning
    # For production, consider maintaining a user:session index
    pattern = "session:*"
    async for key in redis_client.scan_iter(match=pattern):
        session_data = await redis_client.hgetall(key)
        if session_data.get("user_id") == user_id:
            await redis_client.delete(key)


def _extract_email_domain(email: str) -> str:
    """Extract domain from email address."""
    if "@" not in email:
        raise AuthError("Invalid email address")
    return email.split("@")[-1].lower()


def _is_email_domain_allowed(email: str, allowed_domains: str | None) -> bool:
    """Check if email domain is in allowed list."""
    if not allowed_domains:
        return False

    domain = _extract_email_domain(email)
    allowed = [d.strip().lower() for d in allowed_domains.split(",") if d.strip()]
    return domain in allowed


async def _validate_invite_code(invite_code: str, redis_client: redis.Redis) -> bool:
    """
    Validate an invite code.

    Invite codes are stored in Redis with format:
    - invite:{code} -> { "uses_remaining": int, "created_by": user_id }
    """
    invite_key = f"invite:{invite_code}"
    invite_data = await redis_client.hgetall(invite_key)

    if not invite_data:
        return False

    uses_remaining = int(invite_data.get("uses_remaining", 0))
    if uses_remaining <= 0:
        return False

    # Decrement uses
    await redis_client.hincrby(invite_key, "uses_remaining", -1)
    return True


async def validate_registration(
    session: AsyncSession,
    email: str,
    invite_code: str | None = None,
) -> None:
    """
    Validate registration based on system settings.

    Args:
        session: Database session
        email: User's email address
        invite_code: Optional invite code for invite-only mode

    Raises:
        AuthError: If registration is not allowed or validation fails
    """
    system_settings = await SystemSettings.get(session)

    # Check if registration is open
    if not system_settings.is_registration_open:
        raise AuthError(
            "Registration is currently closed",
            status.HTTP_403_FORBIDDEN,
        )

    registration_mode = system_settings.registration_mode

    if registration_mode == RegistrationMode.PUBLIC:
        # No additional validation needed
        return

    elif registration_mode == RegistrationMode.EMAIL_RESTRICTED:
        if not system_settings.allowed_email_domains:
            raise AuthError(
                "Email domain restrictions are not configured",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not _is_email_domain_allowed(email, system_settings.allowed_email_domains):
            allowed = system_settings.allowed_email_domains
            raise AuthError(
                f"Email domain not allowed. Allowed domains: {allowed}",
                status.HTTP_403_FORBIDDEN,
            )

    elif registration_mode == RegistrationMode.INVITE:
        if not invite_code:
            raise AuthError(
                "Invite code is required for registration",
                status.HTTP_403_FORBIDDEN,
            )

        redis_client = await get_redis()
        if not await _validate_invite_code(invite_code, redis_client):
            raise AuthError(
                "Invalid or expired invite code",
                status.HTTP_403_FORBIDDEN,
            )


async def register_user(
    session: AsyncSession,
    username: str,
    email: str,
    password: str,
    invite_code: str | None = None,
    accepted_tos: bool = False,
) -> User:
    """
    Register a new user with validation based on system settings.

    Args:
        session: Database session
        username: Desired username
        email: User's email address
        password: Plain text password
        invite_code: Optional invite code for invite-only mode
        accepted_tos: Whether user accepted Terms of Service

    Returns:
        Created User object

    Raises:
        AuthError: If validation fails or user already exists
    """
    # Validate registration settings
    await validate_registration(session, email, invite_code)

    # Check if username already exists
    result = await session.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        raise AuthError("Username already taken", status.HTTP_409_CONFLICT)

    # Check if email already exists
    result = await session.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise AuthError("Email already registered", status.HTTP_409_CONFLICT)

    # Validate password length
    if len(password) < settings.password_min_length:
        raise AuthError(
            f"Password must be at least {settings.password_min_length} characters",
            status.HTTP_400_BAD_REQUEST,
        )

    # Create user
    user = User(
        username=username,
        email=email,
        password_hash=get_password_hash(password),
        accepted_tos=accepted_tos,
        oauth_provider="local",
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


async def authenticate_user(
    session: AsyncSession,
    username_or_email: str,
    password: str,
) -> User:
    """
    Authenticate a user with username/email and password.

    Args:
        session: Database session
        username_or_email: Username or email
        password: Plain text password

    Returns:
        User object if authentication succeeds

    Raises:
        AuthError: If authentication fails
    """
    # Try to find user by username or email
    result = await session.execute(
        select(User).where(
            (User.username == username_or_email) | (User.email == username_or_email)
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise AuthError("Invalid credentials", status.HTTP_401_UNAUTHORIZED)

    if user.is_banned:
        raise AuthError("Account has been banned", status.HTTP_403_FORBIDDEN)

    if not user.password_hash:
        raise AuthError(
            "This account uses OAuth authentication",
            status.HTTP_400_BAD_REQUEST,
        )

    if not verify_password(password, user.password_hash):
        raise AuthError("Invalid credentials", status.HTTP_401_UNAUTHORIZED)

    return user


async def get_event_state(session: AsyncSession) -> EventState:
    """
    Get the current CTF event state.

    Returns:
        EventState: PRE_EVENT, RUNNING, FROZEN, or ENDED
    """
    system_settings = await SystemSettings.get(session)

    # If platform is paused, treat as FROZEN
    if system_settings.is_paused:
        return EventState.FROZEN

    now = datetime.now(timezone.utc)
    start_time = system_settings.event_start_time
    end_time = system_settings.event_end_time

    # No start time set - event not configured
    if start_time is None:
        return EventState.PRE_EVENT

    # Before start time
    if now < start_time:
        return EventState.PRE_EVENT

    # After end time (if set)
    if end_time is not None and now > end_time:
        return EventState.ENDED

    # Between start and end (or no end set)
    return EventState.RUNNING


async def require_event_running(session: AsyncSession) -> None:
    """
    Require that the event is currently running.

    Raises:
        HTTPException: If event is not in RUNNING state
    """
    state = await get_event_state(session)

    if state == EventState.PRE_EVENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CTF event has not started yet",
        )
    elif state == EventState.ENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CTF event has ended",
        )
    elif state == EventState.FROZEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CTF event is currently frozen",
        )
    # RUNNING is allowed


async def get_current_user_from_session(
    session: AsyncSession,
    request: Request,
    session_cookie: str | None = None,
    paranoid_mode: bool = True,
) -> User:
    """
    Get the current user from session cookie.

    Args:
        session: Database session
        request: FastAPI request object
        session_cookie: Session ID from cookie
        paranoid_mode: If True, validate fingerprint binding

    Returns:
        User object

    Raises:
        AuthError: If session is invalid or user not found
    """
    if not session_cookie:
        raise AuthError("No session provided", status.HTTP_401_UNAUTHORIZED)

    user_id = await validate_session(session_cookie, request, paranoid_mode)

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise AuthError("User not found", status.HTTP_401_UNAUTHORIZED)

    if user.is_banned:
        raise AuthError("Account has been banned", status.HTTP_403_FORBIDDEN)

    return user
