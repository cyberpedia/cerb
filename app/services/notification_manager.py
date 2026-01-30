"""
Notification Manager Service for Cerberus CTF Platform.

Handles notification creation, retrieval, and broadcasting to connected clients.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Manages notifications and WebSocket broadcasting for the platform.

    Provides functionality to:
    - Create and store notifications in the database
    - Broadcast "First Blood" alerts to all connected clients
    - Track connected WebSocket clients by user ID
    """

    def __init__(self) -> None:
        """Initialize the notification manager."""
        # Maps user_id -> set of WebSocket connections
        self._connections: dict[UUID, set[Any]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def register_connection(self, user_id: UUID, websocket: Any) -> None:
        """
        Register a WebSocket connection for a user.

        Args:
            user_id: The user's UUID
            websocket: The WebSocket connection object
        """
        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = set()
            self._connections[user_id].add(websocket)
            logger.info(f"User {user_id} connected to notifications. Total: {len(self._connections[user_id])}")

    async def unregister_connection(self, user_id: UUID, websocket: Any) -> None:
        """
        Unregister a WebSocket connection for a user.

        Args:
            user_id: The user's UUID
            websocket: The WebSocket connection object
        """
        async with self._lock:
            if user_id in self._connections:
                self._connections[user_id].discard(websocket)
                if not self._connections[user_id]:
                    del self._connections[user_id]
                logger.info(f"User {user_id} disconnected from notifications")

    async def broadcast_to_user(self, user_id: UUID, message: dict[str, Any]) -> int:
        """
        Send a message to all connections for a specific user.

        Args:
            user_id: The target user's UUID
            message: The message payload to send

        Returns:
            Number of connections the message was sent to
        """
        connections_to_notify = 0
        async with self._lock:
            user_connections = self._connections.get(user_id, set()).copy()

        for websocket in user_connections:
            try:
                await websocket.send_json(message)
                connections_to_notify += 1
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")

        return connections_to_notify

    async def broadcast_to_all(self, message: dict[str, Any]) -> int:
        """
        Send a message to all connected clients.

        Args:
            message: The message payload to send

        Returns:
            Total number of connections the message was sent to
        """
        total_sent = 0
        async with self._lock:
            all_connections = {k: v.copy() for k, v in self._connections.items()}

        for user_id, connections in all_connections.items():
            for websocket in connections:
                try:
                    await websocket.send_json(message)
                    total_sent += 1
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {e}")

        return total_sent

    async def create_notification(
        self,
        session: AsyncSession,
        user_id: UUID,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        related_entity_id: UUID | None = None,
        related_entity_type: str | None = None,
    ) -> Notification:
        """
        Create a new notification and optionally broadcast it.

        Args:
            session: Database session
            user_id: Target user's UUID
            message: Notification message
            type: Notification type (info, alert, first_blood)
            related_entity_id: Optional related entity UUID
            related_entity_type: Optional related entity type

        Returns:
            The created Notification object
        """
        notification = Notification(
            user_id=user_id,
            message=message,
            notification_type=notification_type.value,
            is_read=False,
            related_entity_id=related_entity_id,
            related_entity_type=related_entity_type,
        )

        session.add(notification)
        await session.commit()
        await session.refresh(notification)

        # Broadcast to the specific user
        await self.broadcast_to_user(
            user_id,
            {
                "type": "notification",
                "data": {
                    "id": str(notification.id),
                    "message": notification.message,
                    "notification_type": notification.notification_type,
                    "is_read": notification.is_read,
                    "created_at": notification.created_at.isoformat(),
                    "related_entity_id": str(notification.related_entity_id) if notification.related_entity_id else None,
                    "related_entity_type": notification.related_entity_type,
                },
            },
        )

        logger.info(f"Created {notification_type.value} notification for user {user_id}")
        return notification

    async def broadcast_first_blood(
        self,
        session: AsyncSession,
        user_id: UUID,
        username: str,
        challenge_id: UUID,
        challenge_name: str,
    ) -> Notification:
        """
        Create and broadcast a "First Blood" notification to all connected clients.

        Args:
            session: Database session
            user_id: The solver's user UUID
            username: The solver's username
            challenge_id: The solved challenge's UUID
            challenge_name: The solved challenge's name

        Returns:
            The created Notification object
        """
        # Create notification for the winner
        message = f"🎯 First Blood! {username} solved '{challenge_name}' first!"
        notification = await self.create_notification(
            session=session,
            user_id=user_id,
            message=message,
            notification_type=NotificationType.FIRST_BLOOD,
            related_entity_id=challenge_id,
            related_entity_type="challenge",
        )

        # Broadcast to all connected users
        broadcast_message = {
            "type": "first_blood",
            "data": {
                "solver_id": str(user_id),
                "solver_username": username,
                "challenge_id": str(challenge_id),
                "challenge_name": challenge_name,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

        total_sent = await self.broadcast_to_all(broadcast_message)
        logger.info(f"Broadcasted First Blood alert to {total_sent} connections")

        return notification

    async def get_user_notifications(
        self,
        session: AsyncSession,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        """
        Retrieve notifications for a user.

        Args:
            session: Database session
            user_id: Target user's UUID
            unread_only: If True, only return unread notifications
            limit: Maximum number of notifications to return
            offset: Number of notifications to skip

        Returns:
            List of Notification objects
        """
        query = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            query = query.where(Notification.is_read == False)

        query = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())

    async def mark_as_read(
        self,
        session: AsyncSession,
        notification_id: UUID,
        user_id: UUID,
    ) -> Notification | None:
        """
        Mark a notification as read.

        Args:
            session: Database session
            notification_id: The notification's UUID
            user_id: The user's UUID (for authorization)

        Returns:
            The updated Notification or None if not found/unauthorized
        """
        query = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        result = await session.execute(query)
        notification = result.scalar_one_or_none()

        if notification:
            notification.is_read = True
            await session.commit()
            await session.refresh(notification)

        return notification

    async def mark_all_as_read(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> int:
        """
        Mark all notifications as read for a user.

        Args:
            session: Database session
            user_id: The user's UUID

        Returns:
            Number of notifications marked as read
        """
        from sqlalchemy import update

        query = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True)
        )
        result = await session.execute(query)
        await session.commit()

        return result.rowcount

    def get_connected_count(self) -> int:
        """Return the total number of connected WebSocket clients."""
        return sum(len(connections) for connections in self._connections.values())

    def get_online_users(self) -> list[UUID]:
        """Return list of user IDs with active connections."""
        return list(self._connections.keys())


# Global notification manager instance
notification_manager = NotificationManager()
