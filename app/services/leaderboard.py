"""
Leaderboard Service for Cerberus CTF Platform.

Handles Redis-backed leaderboards with freeze logic for event states.
Score formula: Points + (1/timestamp) for tie-breaking.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as redis
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.challenge import Challenge, Submission
from app.models.team import Team
from app.models.user import User
from app.services.auth_service import EventState, get_event_state

settings = get_settings()

# Redis key prefixes
LEADERBOARD_USER_KEY = "leaderboard:users"
LEADERBOARD_TEAM_KEY = "leaderboard:teams"
LEADERBOARD_FROZEN_USER_KEY = "leaderboard:frozen:users"
LEADERBOARD_FROZEN_TEAM_KEY = "leaderboard:frozen:teams"
USER_SOLVES_KEY = "user:solves:{user_id}"
TEAM_SOLVES_KEY = "team:solves:{team_id}"

# Redis connection pool
_redis_pool: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Get or create Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")
        _redis_pool = redis.from_url(redis_url, decode_responses=True)
    return _redis_pool


def _calculate_score(points: int, timestamp: datetime) -> float:
    """
    Calculate leaderboard score.
    
    Score = Points + (1/timestamp) where timestamp is Unix timestamp.
    The 1/timestamp component ensures earlier solves rank higher when points are equal.
    
    Args:
        points: Challenge points
        timestamp: Solve timestamp
        
    Returns:
        Float score for Redis sorted set
    """
    unix_ts = timestamp.timestamp()
    # Use a small time bonus that won't affect point-based ranking
    # Normalize to avoid floating point issues with very small numbers
    time_bonus = 1.0 / (unix_ts / 1000000.0)
    return float(points) + time_bonus


def _extract_points_from_score(score: float) -> int:
    """Extract integer points from a score value."""
    return int(score)


class LeaderboardService:
    """Service for managing leaderboards with Redis backend."""
    
    def __init__(self, redis_client: redis.Redis | None = None):
        self._redis = redis_client
    
    async def _get_redis(self) -> redis.Redis:
        """Get Redis client, initializing if necessary."""
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis
    
    async def _get_leaderboard_keys(self, session: AsyncSession) -> tuple[str, str]:
        """
        Get the appropriate leaderboard keys based on event state.
        
        Returns:
            Tuple of (user_key, team_key) to use
        """
        event_state = await get_event_state(session)
        
        if event_state == EventState.FROZEN:
            return (LEADERBOARD_FROZEN_USER_KEY, LEADERBOARD_FROZEN_TEAM_KEY)
        return (LEADERBOARD_USER_KEY, LEADERBOARD_TEAM_KEY)
    
    async def update_user_score(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        challenge_id: uuid.UUID,
        points: int,
        timestamp: datetime,
    ) -> None:
        """
        Update a user's score when they solve a challenge.
        
        Args:
            session: Database session
            user_id: User who solved the challenge
            challenge_id: Challenge that was solved
            points: Points earned
            timestamp: When the solve occurred
        """
        redis_client = await self._get_redis()
        user_key = str(user_id)
        
        # Add challenge to user's solved set (for deduplication)
        user_solves_key = USER_SOLVES_KEY.format(user_id=user_id)
        await redis_client.sadd(user_solves_key, str(challenge_id))
        
        # Calculate new total score by fetching all user's solves from DB
        total_points = await self._calculate_user_total_points(session, user_id)
        
        # Get earliest solve timestamp for tie-breaking
        earliest_ts = await self._get_user_earliest_solve(session, user_id)
        if earliest_ts is None:
            earliest_ts = timestamp
        
        # Calculate score with tie-breaker
        score = _calculate_score(total_points, earliest_ts)
        
        # Update leaderboard
        user_lb_key, _ = await self._get_leaderboard_keys(session)
        await redis_client.zadd(user_lb_key, {user_key: score})
    
    async def update_team_score(
        self,
        session: AsyncSession,
        team_id: uuid.UUID,
        challenge_id: uuid.UUID,
        points: int,
        timestamp: datetime,
    ) -> None:
        """
        Update a team's score when a member solves a challenge.
        
        Team score is the sum of unique challenges solved by any team member.
        
        Args:
            session: Database session
            team_id: Team ID
            challenge_id: Challenge that was solved
            points: Points earned
            timestamp: When the solve occurred
        """
        redis_client = await self._get_redis()
        team_key = str(team_id)
        
        # Add challenge to team's solved set (for deduplication across members)
        team_solves_key = TEAM_SOLVES_KEY.format(team_id=team_id)
        await redis_client.sadd(team_solves_key, str(challenge_id))
        
        # Calculate team score from unique solves
        total_points = await self._calculate_team_total_points(session, team_id)
        
        # Get earliest solve timestamp for tie-breaking
        earliest_ts = await self._get_team_earliest_solve(session, team_id)
        if earliest_ts is None:
            earliest_ts = timestamp
        
        # Calculate score with tie-breaker
        score = _calculate_score(total_points, earliest_ts)
        
        # Update leaderboard
        _, team_lb_key = await self._get_leaderboard_keys(session)
        await redis_client.zadd(team_lb_key, {team_key: score})
    
    async def _calculate_user_total_points(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> int:
        """
        Calculate total points for a user from their unique solves.
        
        Args:
            session: Database session
            user_id: User ID
            
        Returns:
            Total points earned
        """
        result = await session.execute(
            select(func.sum(Challenge.points))
            .join(Submission, Submission.challenge_id == Challenge.id)
            .where(Submission.user_id == user_id)
            .where(Submission.is_correct == True)
        )
        return result.scalar() or 0
    
    async def _calculate_team_total_points(
        self,
        session: AsyncSession,
        team_id: uuid.UUID,
    ) -> int:
        """
        Calculate total points for a team from unique member solves.
        
        Team score = sum of points for unique challenges solved by any member.
        
        Args:
            session: Database session
            team_id: Team ID
            
        Returns:
            Total team points
        """
        # Get all unique challenges solved by any team member
        result = await session.execute(
            select(func.sum(Challenge.points))
            .select_from(
                select(Challenge.points)
                .distinct(Challenge.id)
                .join(Submission, Submission.challenge_id == Challenge.id)
                .join(User, User.id == Submission.user_id)
                .where(User.team_id == team_id)
                .where(Submission.is_correct == True)
                .subquery()
            )
        )
        return result.scalar() or 0
    
    async def _get_user_earliest_solve(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> datetime | None:
        """Get the timestamp of a user's first correct submission."""
        result = await session.execute(
            select(Submission.timestamp)
            .where(Submission.user_id == user_id)
            .where(Submission.is_correct == True)
            .order_by(Submission.timestamp.asc())
            .limit(1)
        )
        row = result.first()
        return row[0] if row else None
    
    async def _get_team_earliest_solve(
        self,
        session: AsyncSession,
        team_id: uuid.UUID,
    ) -> datetime | None:
        """Get the timestamp of a team's first correct submission."""
        result = await session.execute(
            select(Submission.timestamp)
            .join(User, User.id == Submission.user_id)
            .where(User.team_id == team_id)
            .where(Submission.is_correct == True)
            .order_by(Submission.timestamp.asc())
            .limit(1)
        )
        row = result.first()
        return row[0] if row else None
    
    async def get_user_leaderboard(
        self,
        session: AsyncSession,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Get the user leaderboard.
        
        If event is FROZEN, returns cached frozen data.
        
        Args:
            session: Database session
            limit: Maximum number of entries to return
            offset: Offset for pagination
            
        Returns:
            List of leaderboard entries with rank, user info, and score
        """
        redis_client = await self._get_redis()
        user_lb_key, _ = await self._get_leaderboard_keys(session)
        
        # Get ranked entries from Redis
        entries = await redis_client.zrevrange(
            user_lb_key,
            offset,
            offset + limit - 1,
            withscores=True,
        )
        
        # Enrich with user data
        results = []
        for rank, (user_id_str, score) in enumerate(entries, start=offset + 1):
            user_id = uuid.UUID(user_id_str)
            
            # Get user details from database
            result = await session.execute(
                select(User.username, User.team_id)
                .where(User.id == user_id)
            )
            user_row = result.first()
            
            if user_row:
                username, team_id = user_row
                entry = {
                    "rank": rank,
                    "user_id": user_id_str,
                    "username": username,
                    "points": _extract_points_from_score(score),
                    "score": score,
                    "team_id": str(team_id) if team_id else None,
                }
                results.append(entry)
        
        return results
    
    async def get_team_leaderboard(
        self,
        session: AsyncSession,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Get the team leaderboard.
        
        If event is FROZEN, returns cached frozen data.
        
        Args:
            session: Database session
            limit: Maximum number of entries to return
            offset: Offset for pagination
            
        Returns:
            List of leaderboard entries with rank, team info, and score
        """
        redis_client = await self._get_redis()
        _, team_lb_key = await self._get_leaderboard_keys(session)
        
        # Get ranked entries from Redis
        entries = await redis_client.zrevrange(
            team_lb_key,
            offset,
            offset + limit - 1,
            withscores=True,
        )
        
        # Enrich with team data
        results = []
        for rank, (team_id_str, score) in enumerate(entries, start=offset + 1):
            team_id = uuid.UUID(team_id_str)
            
            # Get team details from database
            result = await session.execute(
                select(Team.name, Team.captain_id)
                .where(Team.id == team_id)
            )
            team_row = result.first()
            
            if team_row:
                team_name, captain_id = team_row
                
                # Get member count
                member_count_result = await session.execute(
                    select(func.count(User.id))
                    .where(User.team_id == team_id)
                )
                member_count = member_count_result.scalar() or 0
                
                entry = {
                    "rank": rank,
                    "team_id": team_id_str,
                    "team_name": team_name,
                    "points": _extract_points_from_score(score),
                    "score": score,
                    "member_count": member_count,
                    "captain_id": str(captain_id),
                }
                results.append(entry)
        
        return results
    
    async def get_user_rank(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """
        Get a specific user's rank and score.
        
        Args:
            session: Database session
            user_id: User ID to look up
            
        Returns:
            User's rank info or None if not found
        """
        redis_client = await self._get_redis()
        user_lb_key, _ = await self._get_leaderboard_keys(session)
        
        # Get rank (0-indexed in Redis)
        rank = await redis_client.zrevrank(user_lb_key, str(user_id))
        if rank is None:
            return None
        
        # Get score
        score = await redis_client.zscore(user_lb_key, str(user_id))
        
        # Get user details
        result = await session.execute(
            select(User.username, User.team_id)
            .where(User.id == user_id)
        )
        user_row = result.first()
        
        if not user_row:
            return None
        
        username, team_id = user_row
        
        return {
            "rank": rank + 1,  # Convert to 1-indexed
            "user_id": str(user_id),
            "username": username,
            "points": _extract_points_from_score(score) if score else 0,
            "score": score,
            "team_id": str(team_id) if team_id else None,
        }
    
    async def get_team_rank(
        self,
        session: AsyncSession,
        team_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """
        Get a specific team's rank and score.
        
        Args:
            session: Database session
            team_id: Team ID to look up
            
        Returns:
            Team's rank info or None if not found
        """
        redis_client = await self._get_redis()
        _, team_lb_key = await self._get_leaderboard_keys(session)
        
        # Get rank (0-indexed in Redis)
        rank = await redis_client.zrevrank(team_lb_key, str(team_id))
        if rank is None:
            return None
        
        # Get score
        score = await redis_client.zscore(team_lb_key, str(team_id))
        
        # Get team details
        result = await session.execute(
            select(Team.name, Team.captain_id)
            .where(Team.id == team_id)
        )
        team_row = result.first()
        
        if not team_row:
            return None
        
        team_name, captain_id = team_row
        
        # Get member count
        member_count_result = await session.execute(
            select(func.count(User.id))
            .where(User.team_id == team_id)
        )
        member_count = member_count_result.scalar() or 0
        
        return {
            "rank": rank + 1,  # Convert to 1-indexed
            "team_id": str(team_id),
            "team_name": team_name,
            "points": _extract_points_from_score(score) if score else 0,
            "score": score,
            "member_count": member_count,
            "captain_id": str(captain_id),
        }
    
    async def freeze_leaderboards(self, session: AsyncSession) -> None:
        """
        Freeze the current leaderboard state.
        
        Copies current leaderboard data to frozen keys.
        Should be called when event enters FROZEN state.
        
        Args:
            session: Database session
        """
        redis_client = await self._get_redis()
        
        # Copy user leaderboard to frozen key
        user_entries = await redis_client.zrange(LEADERBOARD_USER_KEY, 0, -1, withscores=True)
        if user_entries:
            await redis_client.zadd(LEADERBOARD_FROZEN_USER_KEY, dict(user_entries))
        
        # Copy team leaderboard to frozen key
        team_entries = await redis_client.zrange(LEADERBOARD_TEAM_KEY, 0, -1, withscores=True)
        if team_entries:
            await redis_client.zadd(LEADERBOARD_FROZEN_TEAM_KEY, dict(team_entries))
    
    async def unfreeze_leaderboards(self) -> None:
        """
        Unfreeze leaderboards by clearing frozen keys.
        
        Should be called when event leaves FROZEN state.
        """
        redis_client = await self._get_redis()
        await redis_client.delete(LEADERBOARD_FROZEN_USER_KEY)
        await redis_client.delete(LEADERBOARD_FROZEN_TEAM_KEY)
    
    async def rebuild_leaderboards(self, session: AsyncSession) -> None:
        """
        Rebuild leaderboards from database.
        
        Useful for initialization or recovery. Processes all submissions
        and recalculates scores.
        
        Args:
            session: Database session
        """
        redis_client = await self._get_redis()
        
        # Clear existing leaderboards
        await redis_client.delete(LEADERBOARD_USER_KEY)
        await redis_client.delete(LEADERBOARD_TEAM_KEY)
        await redis_client.delete(LEADERBOARD_FROZEN_USER_KEY)
        await redis_client.delete(LEADERBOARD_FROZEN_TEAM_KEY)
        
        # Rebuild user leaderboard
        user_solves_result = await session.execute(
            select(
                User.id,
                func.sum(Challenge.points),
                func.min(Submission.timestamp),
            )
            .join(Submission, Submission.user_id == User.id)
            .join(Challenge, Challenge.id == Submission.challenge_id)
            .where(Submission.is_correct == True)
            .group_by(User.id)
        )
        
        user_entries = {}
        for user_id, total_points, earliest_ts in user_solves_result.all():
            if total_points and earliest_ts:
                score = _calculate_score(int(total_points), earliest_ts)
                user_entries[str(user_id)] = score
        
        if user_entries:
            await redis_client.zadd(LEADERBOARD_USER_KEY, user_entries)
        
        # Rebuild team leaderboard
        team_solves_result = await session.execute(
            select(
                Team.id,
                func.sum(Challenge.points),
                func.min(Submission.timestamp),
            )
            .select_from(
                select(Team.id, Challenge.points, Submission.timestamp)
                .distinct(Team.id, Challenge.id)
                .join(User, User.team_id == Team.id)
                .join(Submission, Submission.user_id == User.id)
                .join(Challenge, Challenge.id == Submission.challenge_id)
                .where(Submission.is_correct == True)
                .subquery()
            )
            .group_by(Team.id)
        )
        
        team_entries = {}
        for team_id, total_points, earliest_ts in team_solves_result.all():
            if total_points and earliest_ts:
                score = _calculate_score(int(total_points), earliest_ts)
                team_entries[str(team_id)] = score
        
        if team_entries:
            await redis_client.zadd(LEADERBOARD_TEAM_KEY, team_entries)


# Global service instance
_leaderboard_service: LeaderboardService | None = None


async def get_leaderboard_service() -> LeaderboardService:
    """Get or create the leaderboard service singleton."""
    global _leaderboard_service
    if _leaderboard_service is None:
        redis_client = await get_redis()
        _leaderboard_service = LeaderboardService(redis_client)
    return _leaderboard_service
