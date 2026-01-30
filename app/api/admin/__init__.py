"""
Admin API Routes Package.

Aggregates all admin-related API endpoints:
- config: Dynamic branding and theming configuration
- cms: Content management system for static pages
- ops: Administrative operations (stats, docker, user import, impersonation)
"""

from fastapi import APIRouter

from app.api.admin import cms, config, ops

# Create main admin router
admin_router = APIRouter()

# Include all admin sub-routers
# Config router (already has prefix in its routes)
admin_router.include_router(config.router)

# CMS router (already has prefix in its routes)
admin_router.include_router(cms.router)

# Ops router (already has prefix in its routes)
admin_router.include_router(ops.router)

__all__ = ["admin_router"]
