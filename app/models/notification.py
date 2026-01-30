"""
Notification model for Cerberus CTF Platform.

Stores user notifications with types: info, alert, first_blood.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class NotificationType(str, Enum):
    """Notification type enumeration."""

    INFO = "info"
    ALERT = "alert"
    FIRST_BLOOD = "first_blood"


class Notification(Base):
    """Notification model for storing user alerts and messages."""

    __tablename__ = "notifications"

    # Foreign key to user
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Notification content
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    notification_type: Mapped[str] = mapped_column(
        String(20),
        default=NotificationType.INFO.value,
        nullable=False,
        comment="info, alert, or first_blood",
    )

    # Read status
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Optional: related entity (e.g., challenge ID for first blood)
    related_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    related_entity_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Type of related entity (e.g., challenge, team)",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="notifications",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Notification(id={self.id}, user_id={self.user_id}, "
            f"type={self.notification_type}, is_read={self.is_read})>"
        )
