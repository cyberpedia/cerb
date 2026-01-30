"""
Dynamic Instance model for Cerberus CTF Platform.
Manages per-user/team challenge instances.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.challenge import Challenge


class DynamicInstance(Base):
    """
    Dynamic Instance model for managing per-user challenge containers.
    
    Each user/team gets their own isolated instance of a challenge.
    """

    __tablename__ = "dynamic_instances"

    # Container Info
    active_container_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="Docker container ID",
    )
    container_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Human-readable container name",
    )

    # Network Info
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="Assigned IP address (IPv4/IPv6)",
    )
    port_mappings: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Port mappings: {internal: external}",
    )

    # Relationships
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

    # Lifecycle
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Instance expiration time",
    )
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last user access for idle detection",
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        comment="pending, running, stopped, error",
    )
    error_message: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Metadata
    instance_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Additional instance metadata",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="dynamic_instances")
    challenge: Mapped["Challenge"] = relationship(
        "Challenge",
        back_populates="dynamic_instances",
    )

    def __repr__(self) -> str:
        return (
            f"<DynamicInstance("
            f"user={self.user_id}, "
            f"challenge={self.challenge_id}, "
            f"status={self.status})>"
        )
