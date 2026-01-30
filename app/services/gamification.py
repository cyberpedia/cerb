"""
Gamification Service for Cerberus CTF Platform.

Handles team management (create, join) and badge awarding system.
Badges include: First Blood, Streak, and Category Completion.
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.challenge import Challenge, Submission
from app.models.team import Team
from app.models.user import User
from app.services.leaderboard import get_leaderboard_service


class BadgeType(str, Enum):
    """Types of badges that can be awarded."""
    
    FIRST_BLOOD = "first_blood"
    STREAK = "streak"
    CATEGORY_COMPLETION = "category_completion"


class StreakLevel(str, Enum):
    """Streak badge levels."""
    
    BRONZE = "bronze"  # 3 solves in 24h
    SILVER = "silver"  # 5 solves in 24h
    GOLD = "gold"      # 10 solves in 24h


class TeamError(Exception):
    """Custom team management error."""
    
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class BadgeError(Exception):
    """Custom badge awarding error."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


# Badge configuration
BADGE_CONFIG = {
    BadgeType.FIRST_BLOOD: {
        "name": "First Blood",
        "description": "Be the first to solve a challenge",
        "icon": "🩸",
    },
    BadgeType.STREAK: {
        StreakLevel.BRONZE: {
            "name": "Hot Streak (Bronze)",
            "description": "Solve 3 challenges within 24 hours",
            "icon": "🔥",
            "solves_required": 3,
            "time_window_hours": 24,
        },
        StreakLevel.SILVER: {
            "name": "Hot Streak (Silver)",
            "description": "Solve 5 challenges within 24 hours",
            "icon": "🔥🔥",
            "solves_required": 5,
            "time_window_hours": 24,
        },
        StreakLevel.GOLD: {
            "name": "Hot Streak (Gold)",
            "description": "Solve 10 challenges within 24 hours",
            "icon": "🔥🔥🔥",
            "solves_required": 10,
            "time_window_hours": 24,
        },
    },
    BadgeType.CATEGORY_COMPLETION: {
        "name": "Category Master",
        "description": "Solve all challenges in a category",
        "icon": "🏆",
    },
}


class TeamService:
    """Service for managing teams."""
    
    INVITE_CODE_LENGTH = 32
    MAX_TEAM_NAME_LENGTH = 100
    MAX_TEAM_DESCRIPTION_LENGTH = 500
    MAX_MEMBERS_PER_TEAM = 10
    
    async def create_team(
        self,
        session: AsyncSession,
        captain_id: uuid.UUID,
        name: str,
        description: str | None = None,
    ) -> Team:
        """
        Create a new team.
        
        Args:
            session: Database session
            captain_id: User ID of the team captain
            name: Team name (must be unique)
            description: Optional team description
            
        Returns:
            Newly created Team instance
            
        Raises:
            TeamError: If validation fails or user already in a team
        """
        # Validate name
        if not name or len(name.strip()) < 3:
            raise TeamError("Team name must be at least 3 characters long")
        
        if len(name) > self.MAX_TEAM_NAME_LENGTH:
            raise TeamError(f"Team name must not exceed {self.MAX_TEAM_NAME_LENGTH} characters")
        
        # Validate description
        if description and len(description) > self.MAX_TEAM_DESCRIPTION_LENGTH:
            raise TeamError(f"Description must not exceed {self.MAX_TEAM_DESCRIPTION_LENGTH} characters")
        
        # Check if user exists and is not already in a team
        result = await session.execute(
            select(User).where(User.id == captain_id)
        )
        captain = result.scalar_one_or_none()
        
        if not captain:
            raise TeamError("User not found", status_code=404)
        
        if captain.team_id is not None:
            raise TeamError("You are already a member of a team. Leave your current team first.")
        
        # Check if team name is unique
        existing_result = await session.execute(
            select(Team).where(Team.name == name.strip())
        )
        if existing_result.scalar_one_or_none():
            raise TeamError("A team with this name already exists")
        
        # Generate unique invite code
        invite_code = self._generate_invite_code()
        while await self._invite_code_exists(session, invite_code):
            invite_code = self._generate_invite_code()
        
        # Create team
        team = Team(
            name=name.strip(),
            description=description.strip() if description else None,
            captain_id=captain_id,
            invite_code=invite_code,
            score=0,
        )
        
        session.add(team)
        await session.flush()  # Flush to get team.id
        
        # Assign captain to team
        captain.team_id = team.id
        
        await session.commit()
        await session.refresh(team)
        
        return team
    
    async def join_team(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        invite_code: str,
    ) -> Team:
        """
        Join a team using an invite token.
        
        Args:
            session: Database session
            user_id: User ID joining the team
            invite_code: Team invite code
            
        Returns:
            Team instance that was joined
            
        Raises:
            TeamError: If validation fails or team is full
        """
        # Validate invite code format
        if not invite_code or len(invite_code) < 8:
            raise TeamError("Invalid invite code")
        
        # Check if user exists and is not already in a team
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise TeamError("User not found", status_code=404)
        
        if user.team_id is not None:
            raise TeamError("You are already a member of a team. Leave your current team first.")
        
        # Find team by invite code
        result = await session.execute(
            select(Team).where(Team.invite_code == invite_code.strip())
        )
        team = result.scalar_one_or_none()
        
        if not team:
            raise TeamError("Invalid invite code", status_code=404)
        
        # Check team capacity
        member_count_result = await session.execute(
            select(func.count(User.id)).where(User.team_id == team.id)
        )
        member_count = member_count_result.scalar() or 0
        
        if member_count >= self.MAX_MEMBERS_PER_TEAM:
            raise TeamError(f"Team is full (max {self.MAX_MEMBERS_PER_TEAM} members)")
        
        # Add user to team
        user.team_id = team.id
        
        # Update team score to include new member's contributions
        await self._recalculate_team_score(session, team.id)
        
        await session.commit()
        await session.refresh(team)
        
        # Update leaderboard
        leaderboard_service = await get_leaderboard_service()
        await leaderboard_service.update_team_score(
            session, team.id, uuid.UUID(int=0), 0, datetime.now(timezone.utc)
        )
        
        return team
    
    async def leave_team(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> None:
        """
        Leave the current team.
        
        If the user is the captain, the team is disbanded.
        
        Args:
            session: Database session
            user_id: User ID leaving the team
            
        Raises:
            TeamError: If user is not in a team
        """
        result = await session.execute(
            select(User, Team)
            .join(Team, User.team_id == Team.id)
            .where(User.id == user_id)
        )
        row = result.first()
        
        if not row:
            raise TeamError("You are not a member of any team")
        
        user, team = row
        
        # Check if user is captain
        if team.captain_id == user_id:
            # Disband team - remove all members
            await session.execute(
                select(User)
                .where(User.team_id == team.id)
            )
            
            # Remove all members from team
            await session.execute(
                select(User)
                .where(User.team_id == team.id)
            )
            members_result = await session.execute(
                select(User).where(User.team_id == team.id)
            )
            for member in members_result.scalars().all():
                member.team_id = None
            
            # Delete team
            await session.delete(team)
        else:
            # Just remove user from team
            user.team_id = None
            
            # Recalculate team score
            await self._recalculate_team_score(session, team.id)
        
        await session.commit()
    
    async def regenerate_invite_code(
        self,
        session: AsyncSession,
        captain_id: uuid.UUID,
    ) -> str:
        """
        Generate a new invite code for the team.
        
        Args:
            session: Database session
            captain_id: Team captain's user ID
            
        Returns:
            New invite code
            
        Raises:
            TeamError: If user is not a team captain
        """
        result = await session.execute(
            select(Team).where(Team.captain_id == captain_id)
        )
        team = result.scalar_one_or_none()
        
        if not team:
            raise TeamError("You are not a captain of any team", status_code=403)
        
        # Generate new unique invite code
        new_code = self._generate_invite_code()
        while await self._invite_code_exists(session, new_code):
            new_code = self._generate_invite_code()
        
        team.invite_code = new_code
        await session.commit()
        
        return new_code
    
    async def get_team_details(
        self,
        session: AsyncSession,
        team_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """
        Get detailed information about a team.
        
        Args:
            session: Database session
            team_id: Team ID
            
        Returns:
            Team details including members and stats
        """
        result = await session.execute(
            select(Team).where(Team.id == team_id)
        )
        team = result.scalar_one_or_none()
        
        if not team:
            return None
        
        # Get members
        members_result = await session.execute(
            select(User.id, User.username, User.avatar_url)
            .where(User.team_id == team_id)
        )
        members = [
            {
                "id": str(m[0]),
                "username": m[1],
                "avatar_url": m[2],
                "is_captain": m[0] == team.captain_id,
            }
            for m in members_result.all()
        ]
        
        # Get unique solves count
        unique_solves_result = await session.execute(
            select(func.count(func.distinct(Submission.challenge_id)))
            .join(User, User.id == Submission.user_id)
            .where(User.team_id == team_id)
            .where(Submission.is_correct == True)
        )
        unique_solves = unique_solves_result.scalar() or 0
        
        return {
            "id": str(team.id),
            "name": team.name,
            "description": team.description,
            "captain_id": str(team.captain_id),
            "members": members,
            "member_count": len(members),
            "score": team.score,
            "unique_solves": unique_solves,
            "created_at": team.created_at.isoformat() if team.created_at else None,
        }
    
    async def _recalculate_team_score(
        self,
        session: AsyncSession,
        team_id: uuid.UUID,
    ) -> int:
        """
        Recalculate team score from unique member solves.
        
        Args:
            session: Database session
            team_id: Team ID
            
        Returns:
            New team score
        """
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
        new_score = result.scalar() or 0
        
        # Update team score
        team_result = await session.execute(
            select(Team).where(Team.id == team_id)
        )
        team = team_result.scalar_one_or_none()
        if team:
            team.score = new_score
        
        return new_score
    
    def _generate_invite_code(self) -> str:
        """Generate a secure random invite code."""
        return secrets.token_urlsafe(self.INVITE_CODE_LENGTH)
    
    async def _invite_code_exists(self, session: AsyncSession, code: str) -> bool:
        """Check if an invite code already exists."""
        result = await session.execute(
            select(Team).where(Team.invite_code == code)
        )
        return result.scalar_one_or_none() is not None


class BadgeService:
    """Service for awarding and managing badges."""
    
    async def check_and_award_badges(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        challenge_id: uuid.UUID,
        timestamp: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Check and award badges after a successful submission.
        
        Args:
            session: Database session
            user_id: User who made the submission
            challenge_id: Challenge that was solved
            timestamp: Submission timestamp (defaults to now)
            
        Returns:
            List of newly awarded badges
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        awarded_badges = []
        
        # Check for First Blood
        first_blood = await self._check_first_blood(session, user_id, challenge_id)
        if first_blood:
            awarded_badges.append(first_blood)
        
        # Check for Streak
        streak = await self._check_streak(session, user_id, timestamp)
        if streak:
            awarded_badges.append(streak)
        
        # Check for Category Completion
        category_completion = await self._check_category_completion(
            session, user_id, challenge_id
        )
        if category_completion:
            awarded_badges.append(category_completion)
        
        return awarded_badges
    
    async def _check_first_blood(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        challenge_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """
        Check if user earned First Blood on a challenge.
        
        First Blood is awarded to the first solver of a challenge.
        
        Args:
            session: Database session
            user_id: User to check
            challenge_id: Challenge that was solved
            
        Returns:
            Badge info if First Blood earned, None otherwise
        """
        # Check if this is the first correct submission for this challenge
        result = await session.execute(
            select(Submission.user_id, Submission.timestamp)
            .where(Submission.challenge_id == challenge_id)
            .where(Submission.is_correct == True)
            .order_by(Submission.timestamp.asc())
            .limit(1)
        )
        first_solve = result.first()
        
        if first_solve and first_solve[0] == user_id:
            # Get challenge info
            challenge_result = await session.execute(
                select(Challenge.title, Challenge.category)
                .where(Challenge.id == challenge_id)
            )
            challenge_row = challenge_result.first()
            
            if challenge_row:
                return {
                    "type": BadgeType.FIRST_BLOOD,
                    "name": BADGE_CONFIG[BadgeType.FIRST_BLOOD]["name"],
                    "description": BADGE_CONFIG[BadgeType.FIRST_BLOOD]["description"],
                    "icon": BADGE_CONFIG[BadgeType.FIRST_BLOOD]["icon"],
                    "challenge_id": str(challenge_id),
                    "challenge_title": challenge_row[0],
                    "category": challenge_row[1],
                    "awarded_at": datetime.now(timezone.utc).isoformat(),
                }
        
        return None
    
    async def _check_streak(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        timestamp: datetime,
    ) -> dict[str, Any] | None:
        """
        Check if user earned a Streak badge.
        
        Streak badges are awarded for solving multiple challenges
        within a 24-hour window.
        
        Args:
            session: Database session
            user_id: User to check
            timestamp: Current solve timestamp
            
        Returns:
            Highest streak badge earned, None if no streak
        """
        # Count solves in the last 24 hours
        time_window = timedelta(hours=24)
        window_start = timestamp - time_window
        
        result = await session.execute(
            select(func.count(Submission.id))
            .where(Submission.user_id == user_id)
            .where(Submission.is_correct == True)
            .where(Submission.timestamp >= window_start)
            .where(Submission.timestamp <= timestamp)
        )
        solve_count = result.scalar() or 0
        
        # Determine highest streak level achieved
        if solve_count >= BADGE_CONFIG[BadgeType.STREAK][StreakLevel.GOLD]["solves_required"]:
            level = StreakLevel.GOLD
        elif solve_count >= BADGE_CONFIG[BadgeType.STREAK][StreakLevel.SILVER]["solves_required"]:
            level = StreakLevel.SILVER
        elif solve_count >= BADGE_CONFIG[BadgeType.STREAK][StreakLevel.BRONZE]["solves_required"]:
            level = StreakLevel.BRONZE
        else:
            return None
        
        config = BADGE_CONFIG[BadgeType.STREAK][level]
        return {
            "type": BadgeType.STREAK,
            "level": level,
            "name": config["name"],
            "description": config["description"],
            "icon": config["icon"],
            "solves_in_window": solve_count,
            "time_window_hours": config["time_window_hours"],
            "awarded_at": datetime.now(timezone.utc).isoformat(),
        }
    
    async def _check_category_completion(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        challenge_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """
        Check if user completed all challenges in a category.
        
        Args:
            session: Database session
            user_id: User to check
            challenge_id: Challenge that was just solved
            
        Returns:
            Badge info if category completed, None otherwise
        """
        # Get the category of the solved challenge
        challenge_result = await session.execute(
            select(Challenge.category)
            .where(Challenge.id == challenge_id)
        )
        category_row = challenge_result.first()
        
        if not category_row:
            return None
        
        category = category_row[0]
        
        # Count total active challenges in this category
        total_result = await session.execute(
            select(func.count(Challenge.id))
            .where(Challenge.category == category)
            .where(Challenge.is_active == True)
        )
        total_challenges = total_result.scalar() or 0
        
        if total_challenges == 0:
            return None
        
        # Count user's solves in this category
        solved_result = await session.execute(
            select(func.count(func.distinct(Submission.challenge_id)))
            .join(Challenge, Challenge.id == Submission.challenge_id)
            .where(Submission.user_id == user_id)
            .where(Submission.is_correct == True)
            .where(Challenge.category == category)
            .where(Challenge.is_active == True)
        )
        solved_count = solved_result.scalar() or 0
        
        # Check if all challenges are solved
        if solved_count >= total_challenges:
            return {
                "type": BadgeType.CATEGORY_COMPLETION,
                "name": BADGE_CONFIG[BadgeType.CATEGORY_COMPLETION]["name"],
                "description": f"{BADGE_CONFIG[BadgeType.CATEGORY_COMPLETION]['description']}: {category}",
                "icon": BADGE_CONFIG[BadgeType.CATEGORY_COMPLETION]["icon"],
                "category": category,
                "challenges_solved": solved_count,
                "total_challenges": total_challenges,
                "awarded_at": datetime.now(timezone.utc).isoformat(),
            }
        
        return None
    
    async def get_user_badges(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """
        Get all badges earned by a user.
        
        Note: This is a placeholder implementation. In a production system,
        badges would be stored in the database. This method calculates
        badges on-the-fly from submission history.
        
        Args:
            session: Database session
            user_id: User ID
            
        Returns:
            List of all earned badges
        """
        badges = []
        
        # Get all first bloods
        first_bloods_result = await session.execute(
            select(Challenge.id, Challenge.title, Challenge.category, Submission.timestamp)
            .join(Submission, Submission.challenge_id == Challenge.id)
            .where(Submission.user_id == user_id)
            .where(Submission.is_correct == True)
            .order_by(Submission.timestamp.asc())
        )
        
        for challenge_id, title, category, timestamp in first_bloods_result.all():
            # Check if this was first blood
            first_result = await session.execute(
                select(Submission.user_id)
                .where(Submission.challenge_id == challenge_id)
                .where(Submission.is_correct == True)
                .order_by(Submission.timestamp.asc())
                .limit(1)
            )
            first_solver = first_result.scalar()
            
            if first_solver == user_id:
                badges.append({
                    "type": BadgeType.FIRST_BLOOD,
                    "name": BADGE_CONFIG[BadgeType.FIRST_BLOOD]["name"],
                    "description": BADGE_CONFIG[BadgeType.FIRST_BLOOD]["description"],
                    "icon": BADGE_CONFIG[BadgeType.FIRST_BLOOD]["icon"],
                    "challenge_id": str(challenge_id),
                    "challenge_title": title,
                    "category": category,
                    "awarded_at": timestamp.isoformat(),
                })
        
        # Calculate streak badges from history
        streak_badges = await self._calculate_historical_streaks(session, user_id)
        badges.extend(streak_badges)
        
        # Calculate category completions
        category_badges = await self._calculate_category_completions(session, user_id)
        badges.extend(category_badges)
        
        return badges
    
    async def _calculate_historical_streaks(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """
        Calculate all streak badges from user's submission history.
        
        Args:
            session: Database session
            user_id: User ID
            
        Returns:
            List of streak badges earned
        """
        # Get all solves ordered by timestamp
        result = await session.execute(
            select(Submission.timestamp)
            .where(Submission.user_id == user_id)
            .where(Submission.is_correct == True)
            .order_by(Submission.timestamp.asc())
        )
        solves = [row[0] for row in result.all()]
        
        if len(solves) < 3:
            return []
        
        badges = []
        time_window = timedelta(hours=24)
        
        # Sliding window to find streaks
        for i in range(len(solves)):
            window_start = solves[i]
            window_end = window_start + time_window
            
            # Count solves in this window
            count = sum(1 for ts in solves[i:] if ts <= window_end)
            
            # Determine badge level
            if count >= 10:
                level = StreakLevel.GOLD
            elif count >= 5:
                level = StreakLevel.SILVER
            elif count >= 3:
                level = StreakLevel.BRONZE
            else:
                continue
            
            config = BADGE_CONFIG[BadgeType.STREAK][level]
            badge = {
                "type": BadgeType.STREAK,
                "level": level,
                "name": config["name"],
                "description": config["description"],
                "icon": config["icon"],
                "solves_in_window": count,
                "time_window_hours": config["time_window_hours"],
                "awarded_at": window_end.isoformat(),
            }
            
            # Avoid duplicates - only add if different from last
            if not badges or badges[-1]["level"] != level or badges[-1]["solves_in_window"] != count:
                badges.append(badge)
        
        return badges
    
    async def _calculate_category_completions(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """
        Calculate category completion badges.
        
        Args:
            session: Database session
            user_id: User ID
            
        Returns:
            List of category completion badges
        """
        # Get all categories with their challenges
        categories_result = await session.execute(
            select(Challenge.category, func.count(Challenge.id))
            .where(Challenge.is_active == True)
            .group_by(Challenge.category)
        )
        categories = {row[0]: row[1] for row in categories_result.all()}
        
        badges = []
        
        for category, total in categories.items():
            # Count user's solves in this category
            solved_result = await session.execute(
                select(func.count(func.distinct(Submission.challenge_id)))
                .join(Challenge, Challenge.id == Submission.challenge_id)
                .where(Submission.user_id == user_id)
                .where(Submission.is_correct == True)
                .where(Challenge.category == category)
                .where(Challenge.is_active == True)
            )
            solved = solved_result.scalar() or 0
            
            if solved >= total:
                # Get completion timestamp (when last challenge was solved)
                last_solve_result = await session.execute(
                    select(func.max(Submission.timestamp))
                    .join(Challenge, Challenge.id == Submission.challenge_id)
                    .where(Submission.user_id == user_id)
                    .where(Submission.is_correct == True)
                    .where(Challenge.category == category)
                    .where(Challenge.is_active == True)
                )
                last_solve = last_solve_result.scalar()
                
                badges.append({
                    "type": BadgeType.CATEGORY_COMPLETION,
                    "name": BADGE_CONFIG[BadgeType.CATEGORY_COMPLETION]["name"],
                    "description": f"{BADGE_CONFIG[BadgeType.CATEGORY_COMPLETION]['description']}: {category}",
                    "icon": BADGE_CONFIG[BadgeType.CATEGORY_COMPLETION]["icon"],
                    "category": category,
                    "challenges_solved": solved,
                    "total_challenges": total,
                    "awarded_at": last_solve.isoformat() if last_solve else datetime.now(timezone.utc).isoformat(),
                })
        
        return badges


# Global service instances
_team_service: TeamService | None = None
_badge_service: BadgeService | None = None


async def get_team_service() -> TeamService:
    """Get or create the team service singleton."""
    global _team_service
    if _team_service is None:
        _team_service = TeamService()
    return _team_service


async def get_badge_service() -> BadgeService:
    """Get or create the badge service singleton."""
    global _badge_service
    if _badge_service is None:
        _badge_service = BadgeService()
    return _badge_service
