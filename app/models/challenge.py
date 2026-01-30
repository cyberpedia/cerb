"""
Challenge and Submission models for Cerberus CTF Platform.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.dynamic_instance import DynamicInstance


class Challenge(Base):
    """Challenge model representing CTF challenges."""

    __tablename__ = "challenges"

    # Basic Info
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
    )

    # Categorization
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="web, crypto, pwn, reverse, forensics, misc, etc.",
    )
    difficulty: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
        comment="easy, medium, hard, insane",
    )
    subtype: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="standard",
        comment="standard, blockchain, ai, cloud",
    )

    # Flag Configuration
    flag: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Flag or regex pattern",
    )
    flag_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="static",
        comment="static, regex, case_insensitive",
    )

    # UI Configuration
    ui_layout_config: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Custom UI layout configuration",
    )

    # Connection Info (for dynamic challenges)
    connection_info: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Connection details: host, port, type, etc.",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    is_dynamic: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Requires dynamic instance per user/team",
    )
    max_attempts: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum submission attempts (null = unlimited)",
    )

    # Metadata
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    docker_image: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Docker image for dynamic challenges",
    )

    # Relationships
    submissions: Mapped[list["Submission"]] = relationship(
        "Submission",
        back_populates="challenge",
        cascade="all, delete-orphan",
    )
    dependencies: Mapped[list["ChallengeDependency"]] = relationship(
        "ChallengeDependency",
        foreign_keys="ChallengeDependency.child_id",
        back_populates="child",
        cascade="all, delete-orphan",
    )
    dependents: Mapped[list["ChallengeDependency"]] = relationship(
        "ChallengeDependency",
        foreign_keys="ChallengeDependency.parent_id",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    dynamic_instances: Mapped[list["DynamicInstance"]] = relationship(
        "DynamicInstance",
        back_populates="challenge",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("ix_challenges_category_difficulty", "category", "difficulty"),
        Index("ix_challenges_subtype", "subtype"),
        Index("ix_challenges_points", "points"),
    )

    def __repr__(self) -> str:
        return f"<Challenge(id={self.id}, title={self.title}, points={self.points})>"


class ChallengeDependency(Base):
    """Challenge dependency model for unlock requirements."""

    __tablename__ = "challenge_dependencies"

    parent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("challenges.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
        comment="Challenge that must be solved first",
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("challenges.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
        comment="Challenge that is unlocked after",
    )

    # Relationships
    parent: Mapped["Challenge"] = relationship(
        "Challenge",
        foreign_keys=[parent_id],
        back_populates="dependents",
    )
    child: Mapped["Challenge"] = relationship(
        "Challenge",
        foreign_keys=[child_id],
        back_populates="dependencies",
    )

    def __repr__(self) -> str:
        return f"<ChallengeDependency(parent={self.parent_id}, child={self.child_id})>"


class Submission(Base):
    """Submission model tracking challenge attempts."""

    __tablename__ = "submissions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("challenges.id", ondelete="CASCADE"),
        nullable=False,
    )
    flag_submitted: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="IPv4 or IPv6 address",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="submissions")
    challenge: Mapped["Challenge"] = relationship(
        "Challenge",
        back_populates="submissions",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "challenge_id",
            name="uix_user_challenge_submission",
            deferrable=True,
            initially="DEFERRED",
        ),
        Index("ix_submissions_user_timestamp", "user_id", "timestamp"),
        Index("ix_submissions_challenge_correct", "challenge_id", "is_correct"),
    )

    def __repr__(self) -> str:
        return f"<Submission(user={self.user_id}, challenge={self.challenge_id}, correct={self.is_correct})>"
