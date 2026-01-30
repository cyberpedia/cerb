"""
Challenge API Endpoints for Cerberus CTF Platform.

Handles challenge board retrieval, flag submission, and challenge statistics.
"""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.dependencies import CurrentUser, DbSession, OptionalUser
from app.services.auth_service import EventState, get_event_state, require_event_running
from app.services.challenge_service import (
    ChallengeBoardItem,
    SubmissionResult,
    get_board_for_user,
    get_challenge_statistics,
    get_user_solves,
    submit_flag,
)

router = APIRouter(prefix="/challenges", tags=["Challenges"])


# ============== Request/Response Models ==============


class FlagSubmissionRequest(BaseModel):
    """Flag submission request."""

    flag: str = Field(..., min_length=1, max_length=500, description="Flag to submit")


class FlagSubmissionResponse(BaseModel):
    """Flag submission response."""

    result: str = Field(..., description="Submission result: correct, incorrect, etc.")
    message: str | None = Field(None, description="Success or informational message")
    error: str | None = Field(None, description="Error message if submission failed")
    points: int | None = Field(None, description="Points awarded (if correct)")
    attempts_remaining: int | None = Field(
        None, description="Remaining attempts (if incorrect and max_attempts set)"
    )


class ChallengeResponse(BaseModel):
    """Challenge data for board display."""

    id: str
    title: str
    description: str
    points: int
    category: str
    difficulty: str
    subtype: str
    status: str
    ui_layout_config: dict[str, Any]
    is_dynamic: bool
    max_attempts: int | None
    attempt_count: int
    connection_info: dict[str, Any] | None = None
    solved_at: str | None = None


class ChallengeBoardResponse(BaseModel):
    """Challenge board response."""

    challenges: list[ChallengeResponse]
    total_points: int
    user_points: int
    solved_count: int
    total_count: int


class ChallengeStatisticsResponse(BaseModel):
    """Challenge statistics response."""

    challenge_id: str
    solve_count: int
    attempt_count: int
    first_blood: dict[str, Any] | None


class UserSolvesResponse(BaseModel):
    """User solves response."""

    solves: list[dict[str, Any]]
    total_points: int
    solve_count: int


# ============== Helper Functions ==============


def board_item_to_response(item: ChallengeBoardItem) -> ChallengeResponse:
    """Convert ChallengeBoardItem to ChallengeResponse."""
    data = item.to_dict()
    return ChallengeResponse(**data)


# ============== API Endpoints ==============


@router.get("/board", response_model=ChallengeBoardResponse)
async def get_challenge_board(
    session: DbSession,
    user: OptionalUser,
) -> ChallengeBoardResponse:
    """
    Get the challenge board for the current user.

    Returns all challenges with their computed status based on:
    - Authentication status
    - Challenge dependencies
    - Previous solves

    Unauthenticated users see only root challenges as VISIBLE_LOCKED.
    Authenticated users see challenges with appropriate status:
    - LOCKED: Hidden (not returned)
    - VISIBLE_LOCKED: Visible but requires solving prerequisites
    - OPEN: Available to solve
    - SOLVED: Already solved
    """
    board_items = await get_board_for_user(session, user)

    # Calculate statistics
    total_points = sum(item.points for item in board_items)
    user_points = sum(
        item.points for item in board_items if item.status.value == "solved"
    )
    solved_count = sum(1 for item in board_items if item.status.value == "solved")

    # Convert to response models
    challenges = [board_item_to_response(item) for item in board_items]

    return ChallengeBoardResponse(
        challenges=challenges,
        total_points=total_points,
        user_points=user_points,
        solved_count=solved_count,
        total_count=len(challenges),
    )


@router.post(
    "/{challenge_id}/submit",
    response_model=FlagSubmissionResponse,
    status_code=status.HTTP_200_OK,
)
async def submit_challenge_flag(
    challenge_id: uuid.UUID,
    request_data: FlagSubmissionRequest,
    session: DbSession,
    user: CurrentUser,
    request: Request,
) -> FlagSubmissionResponse:
    """
    Submit a flag for a challenge.

    Requires authentication and the challenge must be unlocked.
    Supports multiple flag modes: static, case_insensitive, regex.

    Returns the result of the submission with appropriate messaging.
    """
    # Check if event is running
    event_state = await get_event_state(session)
    if event_state != EventState.RUNNING:
        # Allow admins to submit flags even when event is not running
        if user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Flag submission is only allowed when the event is running",
            )

    # Get client IP
    ip_address = request.client.host if request.client else None

    # Process submission
    result, details = await submit_flag(
        session=session,
        user=user,
        challenge_id=challenge_id,
        submitted_flag=request_data.flag,
        ip_address=ip_address,
    )

    # Build response based on result
    if result == SubmissionResult.CORRECT:
        return FlagSubmissionResponse(
            result="correct",
            message=details.get("message"),
            points=details.get("points"),
        )
    elif result == SubmissionResult.ALREADY_SOLVED:
        return FlagSubmissionResponse(
            result="already_solved",
            message=details.get("message"),
        )
    elif result == SubmissionResult.INCORRECT:
        return FlagSubmissionResponse(
            result="incorrect",
            error=details.get("error"),
            attempts_remaining=details.get("attempts_remaining"),
        )
    elif result == SubmissionResult.RATE_LIMITED:
        return FlagSubmissionResponse(
            result="rate_limited",
            error=details.get("error"),
        )
    elif result == SubmissionResult.CHALLENGE_LOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=details.get("error"),
        )
    else:
        return FlagSubmissionResponse(
            result="error",
            error=details.get("error", "Unknown error"),
        )


@router.get("/{challenge_id}/statistics", response_model=ChallengeStatisticsResponse)
async def get_challenge_stats(
    challenge_id: uuid.UUID,
    session: DbSession,
    user: OptionalUser,
) -> ChallengeStatisticsResponse:
    """
    Get statistics for a specific challenge.

    Returns solve count, attempt count, and first blood information.
    Available to all users (authenticated or not).
    """
    stats = await get_challenge_statistics(session, challenge_id)
    return ChallengeStatisticsResponse(**stats)


@router.get("/my/solves", response_model=UserSolvesResponse)
async def get_my_solves(
    session: DbSession,
    user: CurrentUser,
) -> UserSolvesResponse:
    """
    Get all challenges solved by the current user.

    Returns a list of solve details including challenge info and timestamps.
    """
    solves = await get_user_solves(session, user.id)
    total_points = sum(solve["points"] for solve in solves)

    return UserSolvesResponse(
        solves=solves,
        total_points=total_points,
        solve_count=len(solves),
    )


@router.get("/user/{user_id}/solves", response_model=UserSolvesResponse)
async def get_user_solves_endpoint(
    user_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> UserSolvesResponse:
    """
    Get all challenges solved by a specific user.

    Users can view their own solves. Admins/moderators can view any user's solves.
    """
    # Check permissions
    if current_user.id != user_id and current_user.role not in ("admin", "moderator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own solves",
        )

    solves = await get_user_solves(session, user_id)
    total_points = sum(solve["points"] for solve in solves)

    return UserSolvesResponse(
        solves=solves,
        total_points=total_points,
        solve_count=len(solves),
    )
