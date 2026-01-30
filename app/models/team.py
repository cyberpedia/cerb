"""
Team model for Cerberus CTF Platform.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Team(Base):
    """Team model representing CTF competition teams."""

    __tablename__ = "teams"

    # Identity
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    invite_code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Scoring
    score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        index=True,
    )

    # Captain (Team Leader)
    captain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships
    captain: Mapped["User"] = relationship(
        "User",
        back_populates="owned_teams",
        foreign_keys=[captain_id],
    )
    members: Mapped[list["User"]] = relationship(
        "User",
        back_populates="team",
        foreign_keys="User.team_id",
    )

    # Indexes
    __table_args__ = (
        Index("ix_teams_score_name", "score", "name"),
    )

    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name={self.name}, score={self.score})>"
