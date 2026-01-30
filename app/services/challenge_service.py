"""
Challenge Service for Cerberus CTF Platform.

Handles challenge board generation with dependency resolution,
flag submission and matching, and challenge status tracking.
"""

import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.challenge import Challenge, ChallengeDependency, Submission
from app.models.user import User
from app.services.gamification import get_badge_service
from app.services.leaderboard import get_leaderboard_service


class ChallengeStatus(str, Enum):
    """Challenge status for user board display."""

    LOCKED = "locked"  # Parent challenge(s) not solved, hidden
    VISIBLE_LOCKED = "visible_locked"  # Visible but requires auth/unlock
    OPEN = "open"  # Available to solve
    SOLVED = "solved"  # Already solved by user


class FlagMode(str, Enum):
    """Flag matching modes."""

    STATIC = "static"
    CASE_INSENSITIVE = "case_insensitive"
    REGEX = "regex"


class SubmissionResult(str, Enum):
    """Flag submission result."""

    CORRECT = "correct"
    INCORRECT = "incorrect"
    ALREADY_SOLVED = "already_solved"
    RATE_LIMITED = "rate_limited"
    CHALLENGE_LOCKED = "challenge_locked"
    EVENT_NOT_RUNNING = "event_not_running"


class ChallengeBoardItem:
    """Challenge item for user board with computed status."""

    def __init__(
        self,
        challenge: Challenge,
        status: ChallengeStatus,
        solved_at: datetime | None = None,
        attempt_count: int = 0,
    ):
        self.id = challenge.id
        self.title = challenge.title
        self.description = challenge.description
        self.points = challenge.points
        self.category = challenge.category
        self.difficulty = challenge.difficulty
        self.subtype = challenge.subtype
        self.status = status
        self.ui_layout_config = challenge.ui_layout_config or {}
        self.connection_info = challenge.connection_info
        self.is_dynamic = challenge.is_dynamic
        self.max_attempts = challenge.max_attempts
        self.solved_at = solved_at
        self.attempt_count = attempt_count

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        result = {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "points": self.points,
            "category": self.category,
            "difficulty": self.difficulty,
            "subtype": self.subtype,
            "status": self.status.value,
            "ui_layout_config": self.ui_layout_config,
            "is_dynamic": self.is_dynamic,
            "max_attempts": self.max_attempts,
            "attempt_count": self.attempt_count,
        }

        # Only include connection info if challenge is open or solved
        if self.status in (ChallengeStatus.OPEN, ChallengeStatus.SOLVED):
            result["connection_info"] = self.connection_info

        if self.solved_at:
            result["solved_at"] = self.solved_at.isoformat()

        return result


async def get_solved_challenge_ids(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> set[uuid.UUID]:
    """
    Get set of challenge IDs solved by user.

    Args:
        session: Database session
        user_id: User ID

    Returns:
        Set of solved challenge IDs
    """
    result = await session.execute(
        select(Submission.challenge_id)
        .where(Submission.user_id == user_id)
        .where(Submission.is_correct == True)
    )
    return {row[0] for row in result.all()}


async def get_challenge_attempt_counts(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> dict[uuid.UUID, int]:
    """
    Get attempt counts for all challenges by user.

    Args:
        session: Database session
        user_id: User ID

    Returns:
        Dictionary mapping challenge ID to attempt count
    """
    result = await session.execute(
        select(Submission.challenge_id, func.count(Submission.id))
        .where(Submission.user_id == user_id)
        .group_by(Submission.challenge_id)
    )
    return {row[0]: row[1] for row in result.all()}


async def get_challenge_dependencies(
    session: AsyncSession,
) -> dict[uuid.UUID, list[uuid.UUID]]:
    """
    Get all challenge dependencies as a mapping.

    Returns:
        Dictionary mapping child challenge ID to list of parent IDs
    """
    result = await session.execute(
        select(ChallengeDependency.child_id, ChallengeDependency.parent_id)
    )
    dependencies: dict[uuid.UUID, list[uuid.UUID]] = {}
    for child_id, parent_id in result.all():
        if child_id not in dependencies:
            dependencies[child_id] = []
        dependencies[child_id].append(parent_id)
    return dependencies


async def get_all_active_challenges(
    session: AsyncSession,
) -> list[Challenge]:
    """
    Get all active challenges.

    Args:
        session: Database session

    Returns:
        List of active challenges
    """
    result = await session.execute(
        select(Challenge)
        .where(Challenge.is_active == True)
        .options(selectinload(Challenge.dependencies))
    )
    return list(result.scalars().all())


def check_challenge_unlocked(
    challenge: Challenge,
    solved_ids: set[uuid.UUID],
    dependencies: dict[uuid.UUID, list[uuid.UUID]],
) -> bool:
    """
    Check if a challenge is unlocked based on dependencies.

    Args:
        challenge: Challenge to check
        solved_ids: Set of solved challenge IDs
        dependencies: Dependency mapping (child -> parents)

    Returns:
        True if all parent challenges are solved
    """
    parent_ids = dependencies.get(challenge.id, [])
    if not parent_ids:
        return True  # No dependencies
    return all(parent_id in solved_ids for parent_id in parent_ids)


def match_flag(challenge: Challenge, submitted_flag: str) -> bool:
    """
    Check if submitted flag matches challenge flag based on flag_mode.

    Args:
        challenge: Challenge with flag configuration
        submitted_flag: Flag submitted by user

    Returns:
        True if flag matches
    """
    if challenge.flag_mode == FlagMode.STATIC:
        return challenge.flag == submitted_flag

    elif challenge.flag_mode == FlagMode.CASE_INSENSITIVE:
        return challenge.flag.lower() == submitted_flag.lower()

    elif challenge.flag_mode == FlagMode.REGEX:
        try:
            pattern = re.compile(challenge.flag)
            return bool(pattern.match(submitted_flag))
        except re.error:
            # Invalid regex pattern in challenge config
            return False

    return False


async def get_board_for_user(
    session: AsyncSession,
    user: User | None,
) -> list[ChallengeBoardItem]:
    """
    Get challenge board for a user with dependency resolution.

    For authenticated users:
    - Shows all challenges with appropriate status
    - Respects dependency chain for unlock status
    - Shows solved challenges as SOLVED

    For unauthenticated users:
    - Shows only challenges with no dependencies as VISIBLE_LOCKED
    - All others are LOCKED (hidden)

    Args:
        session: Database session
        user: Current user (None for unauthenticated)

    Returns:
        List of challenge board items with computed status
    """
    challenges = await get_all_active_challenges(session)
    dependencies = await get_challenge_dependencies(session)

    if user is None:
        # Unauthenticated: show only root challenges as VISIBLE_LOCKED
        board_items = []
        for challenge in challenges:
            challenge_deps = dependencies.get(challenge.id, [])
            if not challenge_deps:
                # Root challenge - visible but locked
                board_items.append(
                    ChallengeBoardItem(
                        challenge=challenge,
                        status=ChallengeStatus.VISIBLE_LOCKED,
                    )
                )
            # Challenges with dependencies are LOCKED (not shown)
        return board_items

    # Authenticated user
    solved_ids = await get_solved_challenge_ids(session, user.id)
    attempt_counts = await get_challenge_attempt_counts(session, user.id)

    # Get solve timestamps for solved challenges
    solved_timestamps: dict[uuid.UUID, datetime] = {}
    if solved_ids:
        result = await session.execute(
            select(Submission.challenge_id, Submission.timestamp)
            .where(Submission.user_id == user.id)
            .where(Submission.is_correct == True)
            .where(Submission.challenge_id.in_(solved_ids))
        )
        for challenge_id, timestamp in result.all():
            solved_timestamps[challenge_id] = timestamp

    board_items = []
    for challenge in challenges:
        # Determine status
        if challenge.id in solved_ids:
            status = ChallengeStatus.SOLVED
            solved_at = solved_timestamps.get(challenge.id)
        elif check_challenge_unlocked(challenge, solved_ids, dependencies):
            status = ChallengeStatus.OPEN
            solved_at = None
        else:
            # Check if this challenge has any visible parent
            parent_ids = dependencies.get(challenge.id, [])
            if any(parent_id in solved_ids or parent_id in [
                c.id for c in challenges if not dependencies.get(c.id, [])
            ] for parent_id in parent_ids):
                # Has at least one visible parent - show as visible_locked
                status = ChallengeStatus.VISIBLE_LOCKED
            else:
                # All parents are also locked - hide this challenge
                continue
            solved_at = None

        board_items.append(
            ChallengeBoardItem(
                challenge=challenge,
                status=status,
                solved_at=solved_at,
                attempt_count=attempt_counts.get(challenge.id, 0),
            )
        )

    return board_items


async def submit_flag(
    session: AsyncSession,
    user: User,
    challenge_id: uuid.UUID,
    submitted_flag: str,
    ip_address: str | None = None,
) -> tuple[SubmissionResult, dict[str, Any]]:
    """
    Process a flag submission.

    Args:
        session: Database session
        user: Submitting user
        challenge_id: Challenge ID
        submitted_flag: Flag submitted by user
        ip_address: Optional IP address for logging

    Returns:
        Tuple of (SubmissionResult, details dict)
    """
    # Get challenge
    result = await session.execute(
        select(Challenge).where(Challenge.id == challenge_id)
    )
    challenge = result.scalar_one_or_none()

    if not challenge:
        return SubmissionResult.INCORRECT, {"error": "Challenge not found"}

    if not challenge.is_active:
        return SubmissionResult.CHALLENGE_LOCKED, {"error": "Challenge is inactive"}

    # Check if already solved
    existing_solve = await session.execute(
        select(Submission)
        .where(Submission.user_id == user.id)
        .where(Submission.challenge_id == challenge_id)
        .where(Submission.is_correct == True)
    )
    if existing_solve.scalar_one_or_none():
        return SubmissionResult.ALREADY_SOLVED, {
            "message": "You have already solved this challenge"
        }

    # Check dependencies (challenge must be unlocked)
    solved_ids = await get_solved_challenge_ids(session, user.id)
    dependencies = await get_challenge_dependencies(session)

    if not check_challenge_unlocked(challenge, solved_ids, dependencies):
        return SubmissionResult.CHALLENGE_LOCKED, {
            "error": "Challenge is locked - solve prerequisite challenges first"
        }

    # Check max attempts
    if challenge.max_attempts is not None:
        attempt_count_result = await session.execute(
            select(func.count(Submission.id))
            .where(Submission.user_id == user.id)
            .where(Submission.challenge_id == challenge_id)
        )
        attempt_count = attempt_count_result.scalar() or 0

        if attempt_count >= challenge.max_attempts:
            return SubmissionResult.RATE_LIMITED, {
                "error": f"Maximum attempts ({challenge.max_attempts}) exceeded"
            }

    # Check flag
    is_correct = match_flag(challenge, submitted_flag)

    # Record submission
    submission = Submission(
        user_id=user.id,
        challenge_id=challenge_id,
        flag_submitted=submitted_flag,
        is_correct=is_correct,
        timestamp=datetime.now(timezone.utc),
        ip_address=ip_address,
    )
    session.add(submission)
    await session.commit()

    if is_correct:
        # Update user leaderboard
        leaderboard_service = await get_leaderboard_service()
        await leaderboard_service.update_user_score(
            session, user.id, challenge_id, challenge.points, submission.timestamp
        )
        
        # Update team leaderboard if user is in a team
        if user.team_id:
            await leaderboard_service.update_team_score(
                session, user.team_id, challenge_id, challenge.points, submission.timestamp
            )
        
        # Check and award badges
        badge_service = await get_badge_service()
        awarded_badges = await badge_service.check_and_award_badges(
            session, user.id, challenge_id, submission.timestamp
        )
        
        return SubmissionResult.CORRECT, {
            "message": "Correct!",
            "points": challenge.points,
            "challenge_id": str(challenge_id),
            "badges": awarded_badges,
        }
    else:
        return SubmissionResult.INCORRECT, {
            "error": "Incorrect flag",
            "attempts_remaining": (
                challenge.max_attempts - attempt_count - 1
                if challenge.max_attempts
                else None
            ),
        }


async def get_challenge_statistics(
    session: AsyncSession,
    challenge_id: uuid.UUID,
) -> dict[str, Any]:
    """
    Get statistics for a challenge.

    Args:
        session: Database session
        challenge_id: Challenge ID

    Returns:
        Dictionary with solve count, attempt count, etc.
    """
    # Get solve count
    solve_result = await session.execute(
        select(func.count(Submission.id))
        .where(Submission.challenge_id == challenge_id)
        .where(Submission.is_correct == True)
    )
    solve_count = solve_result.scalar() or 0

    # Get total attempt count
    attempt_result = await session.execute(
        select(func.count(Submission.id))
        .where(Submission.challenge_id == challenge_id)
    )
    attempt_count = attempt_result.scalar() or 0

    # Get first blood (first solver)
    first_blood_result = await session.execute(
        select(Submission, User)
        .join(User, Submission.user_id == User.id)
        .where(Submission.challenge_id == challenge_id)
        .where(Submission.is_correct == True)
        .order_by(Submission.timestamp.asc())
        .limit(1)
    )
    first_blood_row = first_blood_result.first()
    first_blood = None
    if first_blood_row:
        submission, solver = first_blood_row
        first_blood = {
            "user_id": str(solver.id),
            "username": solver.username,
            "solved_at": submission.timestamp.isoformat(),
        }

    return {
        "challenge_id": str(challenge_id),
        "solve_count": solve_count,
        "attempt_count": attempt_count,
        "first_blood": first_blood,
    }


async def get_user_solves(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """
    Get all solves for a user.

    Args:
        session: Database session
        user_id: User ID

    Returns:
        List of solve details
    """
    result = await session.execute(
        select(Submission, Challenge)
        .join(Challenge, Submission.challenge_id == Challenge.id)
        .where(Submission.user_id == user_id)
        .where(Submission.is_correct == True)
        .order_by(Submission.timestamp.asc())
    )

    solves = []
    for submission, challenge in result.all():
        solves.append({
            "challenge_id": str(challenge.id),
            "challenge_title": challenge.title,
            "challenge_category": challenge.category,
            "points": challenge.points,
            "solved_at": submission.timestamp.isoformat(),
        })

    return solves
