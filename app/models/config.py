"""
Configuration models for Dynamic Branding & Theming.

Provides database models for:
- BrandingConfig: Site branding assets and display options
- ThemeConfig: Color schemes and typography settings
- NavItem: Customizable navigation menu items
"""

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.models.base import Base


class BrandingConfig(Base):
    """
    Branding configuration singleton model.
    
    Stores site-wide branding assets like logos, backgrounds,
    and display preferences. Uses singleton pattern like SystemSettings.
    """

    __tablename__ = "branding_config"

    # Singleton enforcement
    singleton_pk: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=1,
        nullable=False,
    )

    # Site Identity
    site_name: Mapped[str] = mapped_column(
        String(100),
        default="Cerberus CTF",
        nullable=False,
        comment="Display name of the site",
    )
    logo_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="URL to site logo image",
    )
    background_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="URL to background image/video",
    )
    footer_text: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Custom footer text/HTML",
    )

    # Display Options
    show_particles: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Show animated particle background effect",
    )

    @classmethod
    async def get(cls, session) -> "BrandingConfig":
        """
        Get or create the singleton branding config instance.
        
        Args:
            session: Async database session
            
        Returns:
            BrandingConfig: The singleton config instance
        """
        from sqlalchemy import select
        
        result = await session.execute(select(cls).where(cls.singleton_pk == 1))
        config = result.scalar_one_or_none()
        
        if config is None:
            config = cls()
            session.add(config)
            await session.commit()
            
        return config

    def to_dict(self) -> dict:
        """Convert config to dictionary for API responses."""
        return {
            "site_name": self.site_name,
            "logo_url": self.logo_url,
            "background_url": self.background_url,
            "footer_text": self.footer_text,
            "show_particles": self.show_particles,
        }

    def __repr__(self) -> str:
        return f"<BrandingConfig(site_name='{self.site_name}', show_particles={self.show_particles})>"


class ThemeConfig(Base):
    """
    Theme configuration singleton model.
    
    Stores color schemes, typography, and visual styling preferences.
    Uses singleton pattern for global theme settings.
    """

    __tablename__ = "theme_config"

    # Singleton enforcement
    singleton_pk: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=1,
        nullable=False,
    )

    # Color Scheme
    primary_color_hex: Mapped[str] = mapped_column(
        String(7),
        default="#3b82f6",
        nullable=False,
        comment="Primary brand color in hex format (e.g., #3b82f6)",
    )
    bg_color_hex: Mapped[str] = mapped_column(
        String(7),
        default="#0f172a",
        nullable=False,
        comment="Background color in hex format (e.g., #0f172a)",
    )

    # Typography
    font_family: Mapped[str] = mapped_column(
        String(100),
        default="Inter, system-ui, sans-serif",
        nullable=False,
        comment="Primary font family stack",
    )

    @validates("primary_color_hex", "bg_color_hex")
    def validate_hex_color(self, key: str, value: str) -> str:
        """Validate hex color format."""
        if value and not value.startswith("#"):
            raise ValueError(f"{key} must start with #")
        if value and len(value) not in (4, 7):
            raise ValueError(f"{key} must be 4 or 7 characters (e.g., #fff or #ffffff)")
        return value

    @classmethod
    async def get(cls, session) -> "ThemeConfig":
        """
        Get or create the singleton theme config instance.
        
        Args:
            session: Async database session
            
        Returns:
            ThemeConfig: The singleton config instance
        """
        from sqlalchemy import select
        
        result = await session.execute(select(cls).where(cls.singleton_pk == 1))
        config = result.scalar_one_or_none()
        
        if config is None:
            config = cls()
            session.add(config)
            await session.commit()
            
        return config

    def to_dict(self) -> dict:
        """Convert config to dictionary for API responses."""
        return {
            "primary_color_hex": self.primary_color_hex,
            "bg_color_hex": self.bg_color_hex,
            "font_family": self.font_family,
        }

    def __repr__(self) -> str:
        return f"<ThemeConfig(primary='{self.primary_color_hex}', bg='{self.bg_color_hex}')>"


class NavItem(Base):
    """
    Navigation menu item model.
    
    Represents a single item in the site's navigation menu.
    Supports ordering and visibility control.
    """

    __tablename__ = "nav_items"

    # Navigation Properties
    label: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Display label for the navigation item",
    )
    url: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="URL or route path (e.g., /challenges or https://external.com)",
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Sort order (lower values appear first)",
    )
    is_visible: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether the item is visible in the navigation",
    )

    # Optional icon (for future use)
    icon: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Optional icon name/class (e.g., 'Home', 'Settings')",
    )

    def to_dict(self) -> dict:
        """Convert nav item to dictionary for API responses."""
        return {
            "id": str(self.id),
            "label": self.label,
            "url": self.url,
            "order_index": self.order_index,
            "is_visible": self.is_visible,
            "icon": self.icon,
        }

    def __repr__(self) -> str:
        return f"<NavItem(label='{self.label}', url='{self.url}', order={self.order_index})>"
