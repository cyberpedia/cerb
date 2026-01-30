"""
Cerberus Models Package

All SQLAlchemy models for the Cerberus CTF Platform.
"""

from app.models.base import Base
from app.models.challenge import Challenge, ChallengeDependency, Submission
from app.models.config import BrandingConfig, NavItem, ThemeConfig
from app.models.dynamic_instance import DynamicInstance
from app.models.notification import Notification, NotificationType
from app.models.static_page import StaticPage
from app.models.system_settings import SystemSettings
from app.models.team import Team
from app.models.user import User

__all__ = [
    # Base
    "Base",
    # User & Team
    "User",
    "Team",
    # Challenges
    "Challenge",
    "ChallengeDependency",
    "Submission",
    # Infrastructure
    "DynamicInstance",
    # Notifications
    "Notification",
    "NotificationType",
    # System
    "SystemSettings",
    # Configuration
    "BrandingConfig",
    "ThemeConfig",
    "NavItem",
    # CMS
    "StaticPage",
]
