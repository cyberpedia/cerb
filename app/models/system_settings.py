"""
System Settings model for Cerberus CTF Platform.
Singleton configuration for platform-wide settings.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.models.base import Base


class SystemSettings(Base):
    """
    System Settings singleton model.
    
    Stores platform-wide configuration as a single row.
    Use SystemSettings.get() to retrieve the singleton instance.
    """

    __tablename__ = "system_settings"

    # Singleton enforcement
    singleton_pk: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=1,
        nullable=False,
    )

    # Event Timing
    event_start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="CTF event start time",
    )
    event_end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="CTF event end time",
    )

    # Platform State
    is_paused: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Pause all platform activities",
    )
    is_registration_open: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Allow new user registrations",
    )

    # Registration Settings
    registration_mode: Mapped[str] = mapped_column(
        String(20),
        default="public",
        nullable=False,
        comment="public, invite, or email_restricted",
    )
    allowed_email_domains: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Comma-separated list of allowed email domains",
    )

    # Scoring Settings
    decay_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Enable dynamic scoring decay",
    )
    decay_min_points: Mapped[int] = mapped_column(
        Integer,
        default=50,
        nullable=False,
        comment="Minimum points after decay",
    )
    decay_solves_threshold: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
        comment="Number of solves before max decay",
    )

    # Platform Metadata
    platform_name: Mapped[str] = mapped_column(
        String(100),
        default="Cerberus CTF",
        nullable=False,
    )
    platform_description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    @validates("registration_mode")
    def validate_registration_mode(self, key: str, value: str) -> str:
        """Validate registration mode value."""
        allowed = {"public", "invite", "email_restricted"}
        if value not in allowed:
            raise ValueError(f"registration_mode must be one of: {allowed}")
        return value

    @classmethod
    async def get(cls, session) -> "SystemSettings":
        """
        Get or create the singleton settings instance.
        
        Args:
            session: Async database session
            
        Returns:
            SystemSettings: The singleton settings instance
        """
        from sqlalchemy import select
        
        result = await session.execute(select(cls).where(cls.singleton_pk == 1))
        settings = result.scalar_one_or_none()
        
        if settings is None:
            settings = cls()
            session.add(settings)
            await session.commit()
            
        return settings

    def __repr__(self) -> str:
        return (
            f"<SystemSettings("
            f"paused={self.is_paused}, "
            f"registration={self.registration_mode})>"
        )
