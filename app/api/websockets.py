"""
WebSocket API Endpoints for Cerberus CTF Platform.

Provides real-time functionality for:
- Terminal/SSH connections to challenge containers
- Notification streaming to connected clients
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.auth_service import decode_token
from app.services.notification_manager import notification_manager
from app.services.orchestrator import ContainerOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])
settings = get_settings()


# ============== Connection Manager ==============

class ConnectionManager:
    """
    Manages WebSocket connections for the application.

    Provides methods to:
    - Accept and track client connections
    - Handle authentication for WebSocket connections
    - Manage connection lifecycle
    """

    def __init__(self) -> None:
        """Initialize the connection manager."""
        self.active_connections: dict[str, set[WebSocket]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        path: str,
        user_id: UUID | None = None,
    ) -> None:
        """
        Accept a WebSocket connection and register it.

        Args:
            websocket: The WebSocket connection
            path: The connection path (e.g., "/notifications")
            user_id: Optional user ID for authenticated connections
        """
        await websocket.accept()
        if path not in self.active_connections:
            self.active_connections[path] = set()

        self.active_connections[path].add(websocket)
        conn_info = f"user_id={user_id}" if user_id else "anonymous"
        logger.info(f"WebSocket connected: {path} ({conn_info})")

    def disconnect(self, websocket: WebSocket, path: str) -> None:
        """
        Remove a WebSocket connection from tracking.

        Args:
            websocket: The WebSocket connection
            path: The connection path
        """
        if path in self.active_connections:
            self.active_connections[path].discard(websocket)
            if not self.active_connections[path]:
                del self.active_connections[path]
        logger.info(f"WebSocket disconnected: {path}")

    async def send_personal_message(
        self,
        message: dict[str, Any],
        websocket: WebSocket,
    ) -> None:
        """
        Send a message to a specific WebSocket connection.

        Args:
            message: The message payload
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast(
        self,
        message: dict[str, Any],
        path: str,
    ) -> None:
        """
        Broadcast a message to all connections on a path.

        Args:
            message: The message payload
            path: Target connection path
        """
        if path not in self.active_connections:
            return

        connections_to_remove = []
        for connection in self.active_connections[path].copy():
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                connections_to_remove.append(connection)

        for conn in connections_to_remove:
            self.active_connections[path].discard(conn)


# Global connection manager
connection_manager = ConnectionManager()


# ============== Authentication Helper ==============

async def authenticate_websocket(
    websocket: WebSocket,
    token: str | None = None,
) -> User | None:
    """
    Authenticate a WebSocket connection using token or session.

    Args:
        websocket: The WebSocket connection
        token: Optional JWT token from query parameter

    Returns:
        User object if authenticated, None otherwise
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.core.database import engine
    from sqlalchemy import select

    # Try JWT token first
    if token:
        try:
            from app.services.auth_service import decode_token

            payload = decode_token(token)
            user_id = payload.get("sub")
            if user_id:
                # Create a temporary session to fetch the user
                async_session_maker = async_sessionmaker(
                    engine, expire_on_commit=False, class_=AsyncSession
                )
                async with async_session_maker() as session:
                    result = await session.execute(
                        select(User).where(User.id == user_id)
                    )
                    user = result.scalar_one_or_none()
                    if user and not user.is_banned:
                        return user
        except Exception as e:
            logger.error(f"WebSocket JWT auth error: {e}")

    # Try session cookie
    session_id = websocket.cookies.get("session_id")
    if session_id:
        try:
            from app.services.auth_service import validate_session

            # Get the user_id from session
            # Note: validate_session requires a request for paranoid mode
            # For WebSocket, we may need to adjust the security model
            return None
        except Exception as e:
            logger.error(f"WebSocket session auth error: {e}")

    return None


# ============== Notification WebSocket ==============

@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str | None = Query(default=None, description="JWT token for authentication"),
):
    """
    WebSocket endpoint for real-time notifications.

    Authentication: Required via JWT token or session cookie.

    Events:
    - Client -> Server: ping (keepalive)
    - Server -> Client: notification (new notification)
    - Server -> Client: first_blood (first blood alert)

    Returns:
        WebSocket connection that streams notifications to the client
    """
    user = await authenticate_websocket(websocket, token)

    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await connection_manager.connect(websocket, "/notifications", user_id=user.id)
    await notification_manager.register_connection(user.id, websocket)

    try:
        while True:
            try:
                # Wait for client messages (e.g., ping)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)

                if data == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})

            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_json({"type": "ping", "timestamp": datetime.utcnow().isoformat()})

    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(websocket, "/notifications")
        await notification_manager.unregister_connection(user.id, websocket)


# ============== Terminal WebSocket ==============

@router.websocket("/terminal/{container_id}")
async def websocket_terminal(
    websocket: WebSocket,
    container_id: str,
    token: str | None = Query(default=None, description="JWT token for authentication"),
):
    """
    WebSocket endpoint for terminal/SSH access to challenge containers.

    Authentication: Required via JWT token or session cookie.

    This endpoint bridges the WebSocket connection to the Docker container's
    SSH stream, providing interactive terminal access.

    Args:
        websocket: The WebSocket connection
        container_id: The Docker container ID or instance UUID
        token: Optional JWT token for authentication

    Returns:
        WebSocket connection bridged to container's SSH stream
    """
    user = await authenticate_websocket(websocket, token)

    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await connection_manager.connect(websocket, f"/terminal/{container_id}", user_id=user.id)

    orchestrator = ContainerOrchestrator()

    try:
        # Validate container exists and is running
        container = orchestrator.get_container(container_id)

        if not container:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        if container.status != "running":
            await websocket.send_json({
                "type": "error",
                "message": "Container is not running",
            })
            await websocket.close(code=status.WS_1011_SERVER_ERROR)
            return

        # Connect to container's SSH stream
        # This is a simplified implementation - in production, you would
        # use paramiko or similar to establish an SSH connection

        # For now, we'll create a bidirectional stream using Docker's API
        exec_id = container.client.api.create_exec(
            container.id,
            cmd=["/bin/sh"],
            stdin=True,
            tty=True,
            detach=True,
        )

        exec_output = container.client.api.exec_start(
            exec_id,
            socket=True,
            stream=True,
        )

        async def forward_to_container():
            """Forward messages from WebSocket to container."""
            try:
                while True:
                    data = await websocket.receive_bytes()
                    if data:
                        exec_output.write(data)
            except Exception as e:
                logger.error(f"Forward to container error: {e}")

        async def forward_to_websocket():
            """Forward output from container to WebSocket."""
            try:
                while True:
                    chunk = exec_output.read(4096)
                    if chunk:
                        await websocket.send_bytes(chunk)
            except Exception as e:
                logger.error(f"Forward to WebSocket error: {e}")

        # Run both directions concurrently
        await asyncio.gather(
            forward_to_container(),
            forward_to_websocket(),
        )

    except WebSocketDisconnect:
        logger.info(f"Terminal disconnected: container={container_id}, user={user.id}")
    except Exception as e:
        logger.error(f"Terminal error: container={container_id}, error={e}")
        await websocket.close(code=status.WS_1011_SERVER_ERROR)
    finally:
        connection_manager.disconnect(websocket, f"/terminal/{container_id}")


# ============== Health Check WebSocket ==============

@router.websocket("/health")
async def websocket_health(websocket: WebSocket):
    """
    WebSocket endpoint for connection health checks.

    Does not require authentication.

    Returns:
        WebSocket that responds to ping with pong
    """
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat(),
                    "connections": {
                        "notifications": len(connection_manager.active_connections.get("/notifications", set())),
                        "total": sum(len(v) for v in connection_manager.active_connections.values()),
                    },
                })
    except WebSocketDisconnect:
        pass


# ============== Connection Info Endpoint ==============

@router.get("/connections")
async def get_connection_info(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get information about active WebSocket connections.

    Requires authentication.

    Returns:
        Dictionary with connection statistics
    """
    if current_user.role not in ("admin", "moderator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return {
        "active_connections": {
            path: len(connections)
            for path, connections in connection_manager.active_connections.items()
        },
        "notification_subscribers": notification_manager.get_connected_count(),
        "online_users": [str(uid) for uid in notification_manager.get_online_users()],
    }
