"""
CMS (Content Management System) API Endpoints for Static Pages.

Provides:
- Public endpoints for retrieving published static pages
- Admin endpoints for CRUD operations on static pages
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import AdminUser, DbSession, OptionalUser
from app.models.static_page import StaticPage

router = APIRouter()


# ============== Request/Response Models ==============


class StaticPageCreateRequest(BaseModel):
    """Request model for creating a static page."""

    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
        description="URL-friendly identifier (lowercase letters, numbers, hyphens)",
    )
    title: str = Field(..., min_length=1, max_length=200, description="Page title")
    content_markdown: str = Field(
        ..., min_length=0, description="Page content in Markdown format"
    )
    meta_description: str | None = Field(
        None, max_length=500, description="Meta description for SEO"
    )
    is_published: bool = Field(default=True, description="Whether the page is publicly visible")


class StaticPageUpdateRequest(BaseModel):
    """Request model for updating a static page."""

    title: str | None = Field(None, min_length=1, max_length=200, description="Page title")
    content_markdown: str | None = Field(None, min_length=0, description="Page content in Markdown format")
    meta_description: str | None = Field(None, max_length=500, description="Meta description for SEO")
    is_published: bool | None = Field(None, description="Whether the page is publicly visible")


class StaticPageResponse(BaseModel):
    """Response model for a static page."""

    id: str
    slug: str
    title: str
    content_markdown: str
    meta_description: str | None
    is_published: bool
    created_at: str
    updated_at: str


class StaticPageListResponse(BaseModel):
    """Response model for listing static pages."""

    pages: list[StaticPageResponse]
    total: int


class StaticPagePublicResponse(BaseModel):
    """Public response model for a static page (excludes internal fields)."""

    slug: str
    title: str
    content_markdown: str
    meta_description: str | None
    updated_at: str


class StaticPageDeleteResponse(BaseModel):
    """Response model for deleting a static page."""

    message: str
    deleted_id: str


# ============== Public Endpoints ==============


@router.get(
    "/api/public/pages",
    response_model=StaticPageListResponse,
    summary="List Public Static Pages",
    description="Retrieve a list of all published static pages (summary only, no content).",
    tags=["Public CMS"],
)
async def list_public_pages(
    session: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> StaticPageListResponse:
    """
    Get a list of all published static pages.
    
    Returns summary information without full content for listing purposes.
    """
    result = await session.execute(
        select(StaticPage)
        .where(StaticPage.is_published == True)
        .order_by(StaticPage.title)
        .offset(skip)
        .limit(limit)
    )
    pages = result.scalars().all()

    # Get total count
    count_result = await session.execute(
        select(StaticPage).where(StaticPage.is_published == True)
    )
    total = len(count_result.scalars().all())

    return StaticPageListResponse(
        pages=[
            StaticPageResponse(
                id=str(page.id),
                slug=page.slug,
                title=page.title,
                content_markdown=page.content_markdown,
                meta_description=page.meta_description,
                is_published=page.is_published,
                created_at=page.created_at.isoformat() if page.created_at else "",
                updated_at=page.updated_at.isoformat() if page.updated_at else "",
            )
            for page in pages
        ],
        total=total,
    )


@router.get(
    "/api/public/pages/{slug}",
    response_model=StaticPagePublicResponse,
    summary="Get Public Static Page",
    description="Retrieve a single published static page by its slug.",
    tags=["Public CMS"],
)
async def get_public_page(
    slug: str,
    session: DbSession,
) -> StaticPagePublicResponse:
    """
    Get a published static page by slug.
    
    Returns the full page content if published.
    """
    result = await session.execute(
        select(StaticPage).where(StaticPage.slug == slug, StaticPage.is_published == True)
    )
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page '{slug}' not found or not published",
        )

    return StaticPagePublicResponse(
        slug=page.slug,
        title=page.title,
        content_markdown=page.content_markdown,
        meta_description=page.meta_description,
        updated_at=page.updated_at.isoformat() if page.updated_at else "",
    )


# ============== Admin Endpoints ==============


@router.get(
    "/api/admin/pages",
    response_model=StaticPageListResponse,
    summary="List All Static Pages",
    description="Retrieve a list of all static pages including unpublished ones.",
    tags=["Admin CMS"],
)
async def list_all_pages(
    admin: AdminUser,
    session: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    include_unpublished: Annotated[bool, Query()] = True,
) -> StaticPageListResponse:
    """
    Get a list of all static pages (admin only).
    
    Includes unpublished pages for management purposes.
    """
    query = select(StaticPage)
    
    if not include_unpublished:
        query = query.where(StaticPage.is_published == True)
    
    query = query.order_by(StaticPage.title).offset(skip).limit(limit)
    result = await session.execute(query)
    pages = result.scalars().all()

    # Get total count
    count_query = select(StaticPage)
    if not include_unpublished:
        count_query = count_query.where(StaticPage.is_published == True)
    count_result = await session.execute(count_query)
    total = len(count_result.scalars().all())

    return StaticPageListResponse(
        pages=[
            StaticPageResponse(
                id=str(page.id),
                slug=page.slug,
                title=page.title,
                content_markdown=page.content_markdown,
                meta_description=page.meta_description,
                is_published=page.is_published,
                created_at=page.created_at.isoformat() if page.created_at else "",
                updated_at=page.updated_at.isoformat() if page.updated_at else "",
            )
            for page in pages
        ],
        total=total,
    )


@router.get(
    "/api/admin/pages/{slug}",
    response_model=StaticPageResponse,
    summary="Get Static Page (Admin)",
    description="Retrieve any static page by slug, including unpublished ones.",
    tags=["Admin CMS"],
)
async def get_page_admin(
    slug: str,
    admin: AdminUser,
    session: DbSession,
) -> StaticPageResponse:
    """
    Get a static page by slug (admin only).
    
    Can retrieve unpublished pages for editing.
    """
    result = await session.execute(select(StaticPage).where(StaticPage.slug == slug))
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page '{slug}' not found",
        )

    return StaticPageResponse(
        id=str(page.id),
        slug=page.slug,
        title=page.title,
        content_markdown=page.content_markdown,
        meta_description=page.meta_description,
        is_published=page.is_published,
        created_at=page.created_at.isoformat() if page.created_at else "",
        updated_at=page.updated_at.isoformat() if page.updated_at else "",
    )


@router.post(
    "/api/admin/pages",
    response_model=StaticPageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Static Page",
    description="Create a new static page.",
    tags=["Admin CMS"],
)
async def create_page(
    admin: AdminUser,
    session: DbSession,
    request: StaticPageCreateRequest,
) -> StaticPageResponse:
    """
    Create a new static page.
    
    The slug must be unique and URL-friendly (lowercase letters, numbers, hyphens only).
    """
    # Check if slug already exists
    existing = await session.execute(
        select(StaticPage).where(StaticPage.slug == request.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Page with slug '{request.slug}' already exists",
        )

    page = StaticPage(
        slug=request.slug,
        title=request.title,
        content_markdown=request.content_markdown,
        meta_description=request.meta_description,
        is_published=request.is_published,
    )

    session.add(page)
    await session.commit()
    await session.refresh(page)

    return StaticPageResponse(
        id=str(page.id),
        slug=page.slug,
        title=page.title,
        content_markdown=page.content_markdown,
        meta_description=page.meta_description,
        is_published=page.is_published,
        created_at=page.created_at.isoformat() if page.created_at else "",
        updated_at=page.updated_at.isoformat() if page.updated_at else "",
    )


@router.put(
    "/api/admin/pages/{slug}",
    response_model=StaticPageResponse,
    summary="Update Static Page",
    description="Update an existing static page.",
    tags=["Admin CMS"],
)
async def update_page(
    slug: str,
    admin: AdminUser,
    session: DbSession,
    request: StaticPageUpdateRequest,
) -> StaticPageResponse:
    """
    Update an existing static page.
    
    Only provided fields will be updated. The slug cannot be changed;
    create a new page if you need a different slug.
    """
    result = await session.execute(select(StaticPage).where(StaticPage.slug == slug))
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page '{slug}' not found",
        )

    # Update fields if provided
    if request.title is not None:
        page.title = request.title
    if request.content_markdown is not None:
        page.content_markdown = request.content_markdown
    if request.meta_description is not None:
        page.meta_description = request.meta_description
    if request.is_published is not None:
        page.is_published = request.is_published

    await session.commit()
    await session.refresh(page)

    return StaticPageResponse(
        id=str(page.id),
        slug=page.slug,
        title=page.title,
        content_markdown=page.content_markdown,
        meta_description=page.meta_description,
        is_published=page.is_published,
        created_at=page.created_at.isoformat() if page.created_at else "",
        updated_at=page.updated_at.isoformat() if page.updated_at else "",
    )


@router.delete(
    "/api/admin/pages/{slug}",
    response_model=StaticPageDeleteResponse,
    summary="Delete Static Page",
    description="Delete a static page permanently.",
    tags=["Admin CMS"],
)
async def delete_page(
    slug: str,
    admin: AdminUser,
    session: DbSession,
) -> StaticPageDeleteResponse:
    """
    Delete a static page permanently.
    
    This action cannot be undone.
    """
    result = await session.execute(select(StaticPage).where(StaticPage.slug == slug))
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page '{slug}' not found",
        )

    page_id = str(page.id)
    await session.delete(page)
    await session.commit()

    return StaticPageDeleteResponse(
        message=f"Page '{slug}' deleted successfully",
        deleted_id=page_id,
    )
