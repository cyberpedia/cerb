"""
Configuration API Endpoints for Dynamic Branding & Theming.

Provides:
- GET /api/public/config: Cached public endpoint for frontend config
- PUT /api/admin/config: Admin endpoint to update all configuration
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AdminUser, DbSession
from app.models.config import BrandingConfig, NavItem, ThemeConfig

router = APIRouter()


# ============== Request/Response Models ==============


class BrandingConfigSchema(BaseModel):
    """Branding configuration schema."""

    site_name: str = Field(..., min_length=1, max_length=100)
    logo_url: str | None = Field(None, max_length=500)
    background_url: str | None = Field(None, max_length=500)
    footer_text: str | None = Field(None, max_length=500)
    show_particles: bool = Field(default=True)


class ThemeConfigSchema(BaseModel):
    """Theme configuration schema."""

    primary_color_hex: str = Field(..., pattern=r"^#[0-9a-fA-F]{3,6}$")
    bg_color_hex: str = Field(..., pattern=r"^#[0-9a-fA-F]{3,6}$")
    font_family: str = Field(..., min_length=1, max_length=100)


class NavItemSchema(BaseModel):
    """Navigation item schema."""

    id: str | None = Field(None, description="Nav item ID (omit for new items)")
    label: str = Field(..., min_length=1, max_length=50)
    url: str = Field(..., min_length=1, max_length=200)
    order_index: int = Field(default=0, ge=0)
    is_visible: bool = Field(default=True)
    icon: str | None = Field(None, max_length=50)


class PublicConfigResponse(BaseModel):
    """Public configuration response for frontend."""

    branding: dict
    theme: dict
    navigation: list[dict]


class AdminConfigUpdateRequest(BaseModel):
    """Admin configuration update request."""

    branding: BrandingConfigSchema | None = None
    theme: ThemeConfigSchema | None = None
    navigation: list[NavItemSchema] | None = None


class AdminConfigResponse(BaseModel):
    """Admin configuration response."""

    branding: dict
    theme: dict
    navigation: list[dict]
    message: str = "Configuration updated successfully"


# ============== Helper Functions ==============


async def get_all_nav_items(session: AsyncSession) -> list[NavItem]:
    """Get all navigation items ordered by order_index."""
    result = await session.execute(
        select(NavItem).order_by(NavItem.order_index.asc())
    )
    return list(result.scalars().all())


async def sync_nav_items(
    session: AsyncSession,
    items_data: list[NavItemSchema],
) -> list[NavItem]:
    """
    Synchronize navigation items with database.
    
    - Updates existing items by ID
    - Creates new items for entries without ID
    - Removes items not present in the request
    """
    import uuid

    # Get existing items
    existing_result = await session.execute(select(NavItem))
    existing_items = {str(item.id): item for item in existing_result.scalars().all()}
    
    # Track which items to keep
    kept_ids = set()
    updated_items = []

    for item_data in items_data:
        if item_data.id and item_data.id in existing_items:
            # Update existing item
            item = existing_items[item_data.id]
            item.label = item_data.label
            item.url = item_data.url
            item.order_index = item_data.order_index
            item.is_visible = item_data.is_visible
            item.icon = item_data.icon
            kept_ids.add(item_data.id)
            updated_items.append(item)
        else:
            # Create new item
            new_item = NavItem(
                label=item_data.label,
                url=item_data.url,
                order_index=item_data.order_index,
                is_visible=item_data.is_visible,
                icon=item_data.icon,
            )
            session.add(new_item)
            updated_items.append(new_item)

    # Remove items not in request
    for existing_id, existing_item in existing_items.items():
        if existing_id not in kept_ids:
            await session.delete(existing_item)

    await session.flush()
    return updated_items


# ============== Public Endpoints ==============


@router.get(
    "/api/public/config",
    response_model=PublicConfigResponse,
    summary="Get Public Configuration",
    description="Retrieve public branding, theme, and navigation configuration for the frontend. "
                "This endpoint is cached and optimized for frequent access.",
    tags=["Public Configuration"],
)
async def get_public_config(
    session: DbSession,
) -> PublicConfigResponse:
    """
    Get public configuration for frontend.
    
    Returns branding settings, theme colors, and visible navigation items.
    This endpoint is designed to be cached by the frontend.
    """
    # Get singleton configs
    branding = await BrandingConfig.get(session)
    theme = await ThemeConfig.get(session)
    
    # Get visible navigation items only
    result = await session.execute(
        select(NavItem)
        .where(NavItem.is_visible == True)
        .order_by(NavItem.order_index.asc())
    )
    nav_items = result.scalars().all()

    return PublicConfigResponse(
        branding=branding.to_dict(),
        theme=theme.to_dict(),
        navigation=[item.to_dict() for item in nav_items],
    )


# ============== Admin Endpoints ==============


@router.get(
    "/api/admin/config",
    response_model=AdminConfigResponse,
    summary="Get Admin Configuration",
    description="Retrieve full configuration including hidden navigation items.",
    tags=["Admin Configuration"],
)
async def get_admin_config(
    admin: AdminUser,
    session: DbSession,
) -> AdminConfigResponse:
    """
    Get full configuration for admin panel.
    
    Returns all settings including hidden navigation items.
    """
    branding = await BrandingConfig.get(session)
    theme = await ThemeConfig.get(session)
    nav_items = await get_all_nav_items(session)

    return AdminConfigResponse(
        branding=branding.to_dict(),
        theme=theme.to_dict(),
        navigation=[item.to_dict() for item in nav_items],
        message="Configuration retrieved successfully",
    )


@router.put(
    "/api/admin/config",
    response_model=AdminConfigResponse,
    summary="Update Configuration",
    description="Update branding, theme, and/or navigation configuration. "
                "Only provided fields will be updated.",
    tags=["Admin Configuration"],
)
async def update_admin_config(
    admin: AdminUser,
    session: DbSession,
    request: AdminConfigUpdateRequest,
) -> AdminConfigResponse:
    """
    Update configuration settings.
    
    Update branding, theme, and/or navigation. Partial updates are supported.
    """
    # Update branding if provided
    if request.branding:
        branding = await BrandingConfig.get(session)
        branding.site_name = request.branding.site_name
        branding.logo_url = request.branding.logo_url
        branding.background_url = request.branding.background_url
        branding.footer_text = request.branding.footer_text
        branding.show_particles = request.branding.show_particles

    # Update theme if provided
    if request.theme:
        theme = await ThemeConfig.get(session)
        theme.primary_color_hex = request.theme.primary_color_hex
        theme.bg_color_hex = request.theme.bg_color_hex
        theme.font_family = request.theme.font_family

    # Update navigation if provided
    if request.navigation is not None:
        await sync_nav_items(session, request.navigation)

    # Commit changes
    await session.commit()

    # Return updated config
    branding = await BrandingConfig.get(session)
    theme = await ThemeConfig.get(session)
    nav_items = await get_all_nav_items(session)

    return AdminConfigResponse(
        branding=branding.to_dict(),
        theme=theme.to_dict(),
        navigation=[item.to_dict() for item in nav_items],
        message="Configuration updated successfully",
    )


@router.post(
    "/api/admin/config/reset",
    response_model=AdminConfigResponse,
    summary="Reset Configuration",
    description="Reset all configuration to default values.",
    tags=["Admin Configuration"],
)
async def reset_config(
    admin: AdminUser,
    session: DbSession,
) -> AdminConfigResponse:
    """
    Reset all configuration to defaults.
    
    WARNING: This will reset branding, theme, and remove all custom navigation items.
    """
    # Reset branding
    branding = await BrandingConfig.get(session)
    branding.site_name = "Cerberus CTF"
    branding.logo_url = None
    branding.background_url = None
    branding.footer_text = None
    branding.show_particles = True

    # Reset theme
    theme = await ThemeConfig.get(session)
    theme.primary_color_hex = "#3b82f6"
    theme.bg_color_hex = "#0f172a"
    theme.font_family = "Inter, system-ui, sans-serif"

    # Clear all navigation items
    result = await session.execute(select(NavItem))
    for item in result.scalars().all():
        await session.delete(item)

    # Add default navigation items
    default_nav = [
        NavItem(label="Home", url="/", order_index=0, is_visible=True),
        NavItem(label="Challenges", url="/challenges", order_index=1, is_visible=True),
        NavItem(label="Scoreboard", url="/scoreboard", order_index=2, is_visible=True),
        NavItem(label="About", url="/about", order_index=3, is_visible=True),
    ]
    for item in default_nav:
        session.add(item)

    await session.commit()

    nav_items = await get_all_nav_items(session)

    return AdminConfigResponse(
        branding=branding.to_dict(),
        theme=theme.to_dict(),
        navigation=[item.to_dict() for item in nav_items],
        message="Configuration reset to defaults",
    )
