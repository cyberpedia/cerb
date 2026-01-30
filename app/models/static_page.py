"""
Static Page model for CMS (Content Management System).

Provides database model for managing static content pages
with markdown support for rich content.
"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StaticPage(Base):
    """
    Static page model for CMS content management.
    
    Stores static content pages that can be managed by administrators.
    Content is stored in markdown format for flexibility.
    """

    __tablename__ = "static_pages"

    # Unique URL-friendly identifier
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="URL-friendly identifier (e.g., 'about', 'rules')",
    )

    # Page title
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Page title displayed in browser and navigation",
    )

    # Content in Markdown format
    content_markdown: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="Page content in Markdown format",
    )

    # SEO and meta fields
    meta_description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Meta description for SEO",
    )

    # Visibility control
    is_published: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether the page is publicly visible",
    )

    def to_dict(self) -> dict:
        """Convert static page to dictionary for API responses."""
        return {
            "id": str(self.id),
            "slug": self.slug,
            "title": self.title,
            "content_markdown": self.content_markdown,
            "meta_description": self.meta_description,
            "is_published": self.is_published,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_public_dict(self) -> dict:
        """Convert static page to public dictionary (excludes internal fields)."""
        return {
            "slug": self.slug,
            "title": self.title,
            "content_markdown": self.content_markdown,
            "meta_description": self.meta_description,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<StaticPage(slug='{self.slug}', title='{self.title}', published={self.is_published})>"
