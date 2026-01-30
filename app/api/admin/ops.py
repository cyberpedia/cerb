"""
Admin Operations API Endpoints.

Provides administrative operations:
- System stats (CPU/RAM usage, container count)
- Docker cleanup operations
- Bulk user import from CSV
- User impersonation for support
"""

import csv
import io
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import docker
import psutil
from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.dependencies import AdminUser, DbSession
from app.models.dynamic_instance import DynamicInstance
from app.models.user import User
from app.services.auth_service import create_access_token, create_session, get_password_hash
from app.services.orchestrator import ContainerOrchestrator, get_orchestrator

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


# ============== Request/Response Models ==============


class SystemStatsResponse(BaseModel):
    """System statistics response."""

    cpu: dict[str, Any] = Field(..., description="CPU usage statistics")
    memory: dict[str, Any] = Field(..., description="Memory usage statistics")
    containers: dict[str, Any] = Field(..., description="Docker container statistics")
    timestamp: str = Field(..., description="ISO timestamp of the stats snapshot")


class DockerPruneResponse(BaseModel):
    """Docker prune operation response."""

    message: str
    space_reclaimed_mb: float
    containers_removed: int
    images_removed: int
    volumes_removed: int


class UserImportResult(BaseModel):
    """Result of a single user import."""

    row: int
    success: bool
    username: str | None
    email: str | None
    error: str | None


class UserImportResponse(BaseModel):
    """Bulk user import response."""

    total: int
    successful: int
    failed: int
    results: list[UserImportResult]


class ImpersonateResponse(BaseModel):
    """User impersonation response."""

    message: str
    impersonated_user_id: str
    impersonated_username: str
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ImpersonateEndResponse(BaseModel):
    """End impersonation response."""

    message: str


# ============== System Stats Endpoints ==============


@router.get(
    "/api/admin/stats",
    response_model=SystemStatsResponse,
    summary="Get System Statistics",
    description="Retrieve current system statistics including CPU/RAM usage and container count.",
    tags=["Admin Operations"],
)
async def get_system_stats(
    admin: AdminUser,
    session: DbSession,
) -> SystemStatsResponse:
    """
    Get system statistics (admin only).
    
    Returns:
    - CPU usage percentage and count
    - Memory usage (total, available, used, percentage)
    - Docker container statistics (running, total, cerberus-managed)
    """
    # CPU stats
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    cpu_stats = {
        "usage_percent": cpu_percent,
        "count": cpu_count,
        "per_cpu_percent": psutil.cpu_percent(interval=0.1, percpu=True),
    }

    # Memory stats
    memory = psutil.virtual_memory()
    memory_stats = {
        "total_mb": round(memory.total / (1024 * 1024), 2),
        "available_mb": round(memory.available / (1024 * 1024), 2),
        "used_mb": round(memory.used / (1024 * 1024), 2),
        "usage_percent": memory.percent,
    }

    # Docker container stats
    container_stats = {
        "running": 0,
        "total": 0,
        "cerberus_managed": 0,
        "error": None,
    }

    try:
        docker_client = docker.from_env()
        containers = docker_client.containers.list(all=True)
        container_stats["total"] = len(containers)
        container_stats["running"] = len(
            [c for c in containers if c.status == "running"]
        )
        container_stats["cerberus_managed"] = len(
            [
                c
                for c in containers
                if c.labels.get("cerberus.managed") == "true"
            ]
        )
    except Exception as e:
        logger.error(f"Failed to get Docker stats: {e}")
        container_stats["error"] = str(e)

    return SystemStatsResponse(
        cpu=cpu_stats,
        memory=memory_stats,
        containers=container_stats,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ============== Docker Operations Endpoints ==============


@router.post(
    "/api/admin/docker/prune",
    response_model=DockerPruneResponse,
    summary="Prune Docker Resources",
    description="Clean up unused Docker containers, networks, images, and volumes.",
    tags=["Admin Operations"],
)
async def docker_prune(
    admin: AdminUser,
    session: DbSession,
) -> DockerPruneResponse:
    """
    Prune unused Docker resources (admin only).
    
    Removes:
    - Stopped containers
    - Unused networks
    - Dangling images
    - Unused volumes
    
    Returns statistics about reclaimed space.
    """
    try:
        docker_client = docker.from_env()
        
        # Prune containers
        container_prune = docker_client.containers.prune()
        containers_removed = len(container_prune.get("ContainersDeleted", []))
        
        # Prune images (dangling only)
        image_prune = docker_client.images.prune(filters={"dangling": True})
        images_removed = len(image_prune.get("ImagesDeleted", []))
        
        # Prune networks
        network_prune = docker_client.networks.prune()
        networks_removed = len(network_prune.get("NetworksDeleted", []))
        
        # Prune volumes
        volume_prune = docker_client.volumes.prune()
        volumes_removed = len(volume_prune.get("VolumesDeleted", []))
        
        # Calculate total space reclaimed
        space_reclaimed = (
            container_prune.get("SpaceReclaimed", 0) +
            image_prune.get("SpaceReclaimed", 0) +
            volume_prune.get("SpaceReclaimed", 0)
        )
        space_reclaimed_mb = round(space_reclaimed / (1024 * 1024), 2)

        logger.info(
            f"Docker prune by admin {admin.username}: "
            f"{containers_removed} containers, {images_removed} images, "
            f"{volumes_removed} volumes removed, {space_reclaimed_mb}MB reclaimed"
        )

        return DockerPruneResponse(
            message="Docker resources pruned successfully",
            space_reclaimed_mb=space_reclaimed_mb,
            containers_removed=containers_removed,
            images_removed=images_removed,
            volumes_removed=volumes_removed,
        )

    except Exception as e:
        logger.error(f"Docker prune failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prune Docker resources: {str(e)}",
        )


# ============== User Import Endpoints ==============


@router.post(
    "/api/admin/users/import",
    response_model=UserImportResponse,
    summary="Bulk Import Users from CSV",
    description="Import multiple users from a CSV file.",
    tags=["Admin Operations"],
)
async def import_users_csv(
    admin: AdminUser,
    session: DbSession,
    file: Annotated[UploadFile, File(description="CSV file with columns: username, email, password, role (optional)")],
) -> UserImportResponse:
    """
    Bulk import users from CSV (admin only).
    
    CSV format:
    - username: Required, unique, 3-50 characters
    - email: Required, unique, valid email
    - password: Required, minimum 8 characters
    - role: Optional, defaults to 'user' (user, admin, moderator)
    
    Returns detailed results for each row, including success/failure status.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV",
        )

    results: list[UserImportResult] = []
    successful = 0
    failed = 0
    row_number = 0

    try:
        content = await file.read()
        csv_file = io.StringIO(content.decode("utf-8"))
        reader = csv.DictReader(csv_file)

        for row in reader:
            row_number += 1
            username = row.get("username", "").strip()
            email = row.get("email", "").strip()
            password = row.get("password", "").strip()
            role = row.get("role", "user").strip() or "user"

            # Validate required fields
            if not username:
                results.append(
                    UserImportResult(
                        row=row_number,
                        success=False,
                        username=None,
                        email=email or None,
                        error="Username is required",
                    )
                )
                failed += 1
                continue

            if not email:
                results.append(
                    UserImportResult(
                        row=row_number,
                        success=False,
                        username=username,
                        email=None,
                        error="Email is required",
                    )
                )
                failed += 1
                continue

            if not password:
                results.append(
                    UserImportResult(
                        row=row_number,
                        success=False,
                        username=username,
                        email=email,
                        error="Password is required",
                    )
                )
                failed += 1
                continue

            # Validate username format
            if not username.isalnum() and "_" not in username:
                results.append(
                    UserImportResult(
                        row=row_number,
                        success=False,
                        username=username,
                        email=email,
                        error="Username must be alphanumeric with underscores only",
                    )
                )
                failed += 1
                continue

            if len(username) < 3 or len(username) > 50:
                results.append(
                    UserImportResult(
                        row=row_number,
                        success=False,
                        username=username,
                        email=email,
                        error="Username must be between 3 and 50 characters",
                    )
                )
                failed += 1
                continue

            # Validate email format
            try:
                from pydantic import validate_email
                validate_email(email)
            except Exception:
                results.append(
                    UserImportResult(
                        row=row_number,
                        success=False,
                        username=username,
                        email=email,
                        error="Invalid email format",
                    )
                )
                failed += 1
                continue

            # Validate password length
            if len(password) < settings.password_min_length:
                results.append(
                    UserImportResult(
                        row=row_number,
                        success=False,
                        username=username,
                        email=email,
                        error=f"Password must be at least {settings.password_min_length} characters",
                    )
                )
                failed += 1
                continue

            # Validate role
            if role not in ("user", "admin", "moderator"):
                results.append(
                    UserImportResult(
                        row=row_number,
                        success=False,
                        username=username,
                        email=email,
                        error="Role must be one of: user, admin, moderator",
                    )
                )
                failed += 1
                continue

            # Check for existing username
            existing = await session.execute(
                select(User).where(User.username == username)
            )
            if existing.scalar_one_or_none():
                results.append(
                    UserImportResult(
                        row=row_number,
                        success=False,
                        username=username,
                        email=email,
                        error="Username already exists",
                    )
                )
                failed += 1
                continue

            # Check for existing email
            existing = await session.execute(
                select(User).where(User.email == email)
            )
            if existing.scalar_one_or_none():
                results.append(
                    UserImportResult(
                        row=row_number,
                        success=False,
                        username=username,
                        email=email,
                        error="Email already registered",
                    )
                )
                failed += 1
                continue

            # Create user
            try:
                user = User(
                    username=username,
                    email=email,
                    password_hash=get_password_hash(password),
                    role=role,
                    accepted_tos=True,
                    oauth_provider="local",
                )
                session.add(user)
                await session.flush()

                results.append(
                    UserImportResult(
                        row=row_number,
                        success=True,
                        username=username,
                        email=email,
                        error=None,
                    )
                )
                successful += 1

            except Exception as e:
                results.append(
                    UserImportResult(
                        row=row_number,
                        success=False,
                        username=username,
                        email=email,
                        error=f"Database error: {str(e)}",
                    )
                )
                failed += 1

        # Commit all successful users
        await session.commit()

        logger.info(
            f"Bulk user import by admin {admin.username}: "
            f"{successful} successful, {failed} failed"
        )

        return UserImportResponse(
            total=row_number,
            successful=successful,
            failed=failed,
            results=results,
        )

    except Exception as e:
        await session.rollback()
        logger.error(f"User import failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process CSV: {str(e)}",
        )


# ============== Impersonation Endpoints ==============


@router.post(
    "/api/admin/impersonate/{user_id}",
    response_model=ImpersonateResponse,
    summary="Impersonate User",
    description="Start impersonating a user for support purposes. Returns a token for the target user.",
    tags=["Admin Operations"],
)
async def impersonate_user(
    user_id: uuid.UUID,
    admin: AdminUser,
    session: DbSession,
    request: Request,
) -> ImpersonateResponse:
    """
    Impersonate a user (admin only).
    
    Allows administrators to act on behalf of another user for support purposes.
    Returns an access token for the target user.
    
    Security:
    - Cannot impersonate other admins
    - Action is logged for audit purposes
    - Original admin session remains valid
    """
    # Get target user
    result = await session.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent impersonating other admins (security measure)
    if target_user.role == "admin" and target_user.id != admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot impersonate other admins",
        )

    # Create impersonation token with shorter expiry
    expires_delta = timedelta(minutes=30)  # Shorter expiry for impersonation
    access_token = create_access_token(
        data={
            "sub": str(target_user.id),
            "impersonated_by": str(admin.id),
            "impersonated_by_username": admin.username,
            "type": "impersonation",
        },
        expires_delta=expires_delta,
    )

    logger.warning(
        f"Admin impersonation: {admin.username} ({admin.id}) is now impersonating "
        f"{target_user.username} ({target_user.id}) from IP {request.client.host if request.client else 'unknown'}"
    )

    return ImpersonateResponse(
        message=f"Now impersonating user: {target_user.username}",
        impersonated_user_id=str(target_user.id),
        impersonated_username=target_user.username,
        access_token=access_token,
        expires_in=30 * 60,  # 30 minutes in seconds
    )


@router.post(
    "/api/admin/impersonate/end",
    response_model=ImpersonateEndResponse,
    summary="End Impersonation",
    description="End the current impersonation session and return to admin account.",
    tags=["Admin Operations"],
)
async def end_impersonation(
    admin: AdminUser,
) -> ImpersonateEndResponse:
    """
    End user impersonation (admin only).
    
    Simply instructs the client to discard the impersonation token
    and revert to using their original admin token.
    """
    logger.info(f"Admin {admin.username} ended impersonation session")

    return ImpersonateEndResponse(
        message="Impersonation ended. Please revert to your original admin token.",
    )
