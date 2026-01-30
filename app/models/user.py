"""
User model for Cerberus CTF Platform.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.challenge import Submission
    from app.models.dynamic_instance import DynamicInstance
    from app.models.notification import Notification
    from app.models.team import Team


class User(Base):
    """User model representing platform participants."""

    __tablename__ = "users"

    # Authentication & Identity
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Hashed password (null for OAuth users)",
    )

    # Profile
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Role & Status
    role: Mapped[str] = mapped_column(
        String(20),
        default="user",
        nullable=False,
        comment="user, admin, or moderator",
    )
    is_banned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Email verification status",
    )
    accepted_tos: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Accepted Terms of Service",
    )

    # OAuth Provider
    oauth_provider: Mapped[str] = mapped_column(
        String(20),
        default="local",
        nullable=False,
        comment="local, github, or google",
    )
    oauth_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Provider-specific user ID",
    )

    # Team Relationship
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    team: Mapped["Team | None"] = relationship(
        "Team",
        back_populates="members",
        foreign_keys=[team_id],
    )
    owned_teams: Mapped[list["Team"]] = relationship(
        "Team",
        back_populates="captain",
        foreign_keys="Team.captain_id",
    )
    submissions: Mapped[list["Submission"]] = relationship(
        "Submission",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    dynamic_instances: Mapped[list["DynamicInstance"]] = relationship(
        "DynamicInstance",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(Notification.created_at)",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "oauth_provider",
            "oauth_id",
            name="uix_oauth_provider_id",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"
