"""
FastAPI Dependencies for Cerberus CTF Platform.

Reusable dependencies for authentication, authorization, and event state management.
"""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.services.auth_service import (
    AuthError,
    EventState,
    create_access_token,
    decode_token,
    get_current_user_from_session,
    get_event_state,
    require_event_running,
)

# Security scheme for API documentation
security = HTTPBearer(auto_error=False)


async def get_db_session() -> AsyncSession:
    """Dependency for getting database sessions."""
    async for session in get_db():
        yield session



async def get_current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    session_cookie: Annotated[str | None, Cookie(alias="session_id")] = None,
    authorization: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
) -> User:
    """
    Get the currently authenticated user.

    Supports both session cookies and Bearer tokens.
    Session cookies are preferred for browser clients.
    Bearer tokens are supported for API clients.

    Args:
        request: FastAPI request object
        session: Database session
        session_cookie: Session ID from cookie
        authorization: Bearer token from Authorization header

    Returns:
        Authenticated User object

    Raises:
        HTTPException: If authentication fails
    """
    # Try session cookie first (for browser clients)
    if session_cookie:
        try:
            return await get_current_user_from_session(
                session, request, session_cookie, paranoid_mode=True
            )
        except AuthError:
            pass  # Fall through to token auth

    # Try Bearer token (for API clients)
    if authorization and authorization.credentials:
        try:
            payload = decode_token(authorization.credentials)
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                )

            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                )

            if user.is_banned:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account has been banned",
                )

            return user
        except AuthError as e:
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message,
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_optional_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    session_cookie: Annotated[str | None, Cookie(alias="session_id")] = None,
    authorization: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
) -> User | None:
    """
    Get the currently authenticated user, or None if not authenticated.

    This is useful for endpoints that work for both authenticated and
    unauthenticated users.
    """
    try:
        return await get_current_user(request, session, session_cookie, authorization)
    except HTTPException:
        return None


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


async def require_admin(user: CurrentUser) -> User:
    """
    Require that the current user is an admin.

    Args:
        user: Current authenticated user

    Returns:
        User object if admin

    Raises:
        HTTPException: If user is not an admin
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


AdminUser = Annotated[User, Depends(require_admin)]


async def require_moderator(user: CurrentUser) -> User:
    """
    Require that the current user is a moderator or admin.

    Args:
        user: Current authenticated user

    Returns:
        User object if moderator or admin

    Raises:
        HTTPException: If user is not a moderator or admin
    """
    if user.role not in ("admin", "moderator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator access required",
        )
    return user


ModeratorUser = Annotated[User, Depends(require_moderator)]


async def get_event_state_dependency(session: Annotated[AsyncSession, Depends(get_db_session)]) -> EventState:
    """
    Get the current CTF event state as a dependency.

    Returns:
        EventState enum value
    """
    return await get_event_state(session)


EventStateDep = Annotated[EventState, Depends(get_event_state_dependency)]


async def require_event_running_dependency(session: Annotated[AsyncSession, Depends(get_db_session)]) -> None:
    """
    Dependency that requires the event to be running.

    Raises:
        HTTPException: If event is not running
    """
    await require_event_running(session)


RequireEventRunning = Depends(require_event_running_dependency)


async def block_during_event(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    blocked_states: list[EventState] | None = None,
) -> None:
    """
    Block access during specific event states.

    Args:
        session: Database session
        blocked_states: List of states to block (defaults to PRE_EVENT and ENDED)

    Raises:
        HTTPException: If current state is in blocked_states
    """
    if blocked_states is None:
        blocked_states = [EventState.PRE_EVENT, EventState.ENDED]

    current_state = await get_event_state(session)

    if current_state in blocked_states:
        state_messages = {
            EventState.PRE_EVENT: "CTF event has not started yet",
            EventState.RUNNING: "CTF event is running",
            EventState.FROZEN: "CTF event is currently frozen",
            EventState.ENDED: "CTF event has ended",
        }
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=state_messages.get(current_state, "Event state restriction"),
        )


async def require_event_not_started(session: Annotated[AsyncSession, Depends(get_db_session)]) -> None:
    """
    Require that the event has not started yet.

    Useful for pre-event setup operations.
    """
    state = await get_event_state(session)
    if state != EventState.PRE_EVENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation is only allowed before the event starts",
        )


RequireEventNotStarted = Depends(require_event_not_started)


async def require_event_started(session: Annotated[AsyncSession, Depends(get_db_session)]) -> None:
    """
    Require that the event has started (running, frozen, or ended).

    Useful for post-event operations that shouldn't happen before start.
    """
    state = await get_event_state(session)
    if state == EventState.PRE_EVENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires the event to have started",
        )


RequireEventStarted = Depends(require_event_started)
