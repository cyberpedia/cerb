"""
Container Orchestrator Service for Cerberus CTF Platform.

Manages dynamic challenge instances with specialized subtypes:
- Standard: Isolated containers with no network access
- Blockchain: Ganache CLI with private key injection
- AI: HuggingFace Transformers with strict memory limits
- Cloud: LocalStack for AWS simulation

Includes automatic lifecycle management to kill containers after 60 minutes.
"""

import asyncio
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import docker
from docker.errors import DockerException, NotFound
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.challenge import Challenge
from app.models.dynamic_instance import DynamicInstance

logger = logging.getLogger(__name__)


class ChallengeSubtype(str, Enum):
    """Challenge subtypes supported by the orchestrator."""

    STANDARD = "standard"
    BLOCKCHAIN = "blockchain"
    AI = "ai"
    CLOUD = "cloud"


class ContainerStatus(str, Enum):
    """Container lifecycle status."""

    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class OrchestratorError(Exception):
    """Base exception for orchestrator errors."""

    pass


class ContainerSpawnError(OrchestratorError):
    """Exception raised when container spawning fails."""

    pass


class ContainerOrchestrator:
    """
    Container Orchestrator for managing dynamic challenge instances.

    Handles specialized container types with different configurations:
    - Standard: Network-isolated containers
    - Blockchain: Ganache CLI with key injection
    - AI: Memory-limited ML containers
    - Cloud: LocalStack AWS simulation
    """

    # Default container images for each subtype
    DEFAULT_IMAGES = {
        ChallengeSubtype.STANDARD: "alpine:latest",
        ChallengeSubtype.BLOCKCHAIN: "trufflesuite/ganache-cli:latest",
        ChallengeSubtype.AI: "huggingface/transformers-pytorch-cpu:latest",
        ChallengeSubtype.CLOUD: "localstack/localstack:latest",
    }

    # Memory limits by subtype (in bytes)
    MEMORY_LIMITS = {
        ChallengeSubtype.STANDARD: 128 * 1024 * 1024,  # 128MB
        ChallengeSubtype.BLOCKCHAIN: 512 * 1024 * 1024,  # 512MB
        ChallengeSubtype.AI: 512 * 1024 * 1024,  # 512MB strict limit
        ChallengeSubtype.CLOUD: 256 * 1024 * 1024,  # 256MB
    }

    # Default instance TTL (60 minutes)
    DEFAULT_TTL_MINUTES = 60

    def __init__(self) -> None:
        """Initialize the orchestrator with Docker client."""
        self.settings = get_settings()
        self._docker_client: docker.DockerClient | None = None
        self._cleanup_task: asyncio.Task | None = None

    @property
    def docker_client(self) -> docker.DockerClient:
        """Get or create Docker client instance."""
        if self._docker_client is None:
            try:
                self._docker_client = docker.from_env()
                # Test connection
                self._docker_client.ping()
                logger.info("Docker client initialized successfully")
            except DockerException as e:
                logger.error(f"Failed to initialize Docker client: {e}")
                raise OrchestratorError(f"Docker connection failed: {e}") from e
        return self._docker_client

    async def spawn_instance(
        self,
        user_id: uuid.UUID,
        challenge_id: uuid.UUID,
        db_session: AsyncSession,
    ) -> DynamicInstance:
        """
        Spawn a new container instance for a user and challenge.

        Args:
            user_id: UUID of the user requesting the instance
            challenge_id: UUID of the challenge
            db_session: Database session for persistence

        Returns:
            DynamicInstance: The created instance record

        Raises:
            ContainerSpawnError: If container creation fails
        """
        # Fetch challenge details
        result = await db_session.execute(
            select(Challenge).where(Challenge.id == challenge_id)
        )
        challenge = result.scalar_one_or_none()

        if not challenge:
            raise ContainerSpawnError(f"Challenge {challenge_id} not found")

        if not challenge.is_dynamic:
            raise ContainerSpawnError(f"Challenge {challenge_id} is not dynamic")

        subtype = ChallengeSubtype(challenge.subtype)

        # Check for existing active instance
        existing = await self._get_active_instance(user_id, challenge_id, db_session)
        if existing:
            logger.info(f"Returning existing instance for user {user_id}, challenge {challenge_id}")
            return existing

        # Generate unique container name
        container_name = f"cerberus-{challenge.subtype}-{user_id.hex[:8]}-{challenge_id.hex[:8]}"

        try:
            # Spawn container based on subtype
            container_info = await self._spawn_by_subtype(
                subtype=subtype,
                container_name=container_name,
                challenge=challenge,
            )

            # Create instance record
            expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=self.DEFAULT_TTL_MINUTES
            )

            instance = DynamicInstance(
                user_id=user_id,
                challenge_id=challenge_id,
                active_container_id=container_info["container_id"],
                container_name=container_name,
                ip_address=container_info.get("ip_address"),
                port_mappings=container_info.get("port_mappings", {}),
                started_at=datetime.now(timezone.utc),
                expires_at=expires_at,
                last_accessed_at=datetime.now(timezone.utc),
                status=ContainerStatus.RUNNING,
                instance_metadata=container_info.get("metadata", {}),
            )

            db_session.add(instance)
            await db_session.commit()
            await db_session.refresh(instance)

            logger.info(
                f"Spawned {subtype} instance {container_name} for user {user_id}"
            )
            return instance

        except Exception as e:
            logger.error(f"Failed to spawn container: {e}")
            raise ContainerSpawnError(f"Container spawn failed: {e}") from e

    async def _spawn_by_subtype(
        self,
        subtype: ChallengeSubtype,
        container_name: str,
        challenge: Challenge,
    ) -> dict[str, Any]:
        """
        Spawn container based on challenge subtype.

        Args:
            subtype: The challenge subtype
            container_name: Unique name for the container
            challenge: Challenge model instance

        Returns:
            Dictionary with container info including ID, ports, metadata
        """
        spawn_methods = {
            ChallengeSubtype.STANDARD: self._spawn_standard,
            ChallengeSubtype.BLOCKCHAIN: self._spawn_blockchain,
            ChallengeSubtype.AI: self._spawn_ai,
            ChallengeSubtype.CLOUD: self._spawn_cloud,
        }

        spawn_method = spawn_methods.get(subtype)
        if not spawn_method:
            raise ContainerSpawnError(f"Unknown subtype: {subtype}")

        return await spawn_method(container_name, challenge)

    async def _spawn_standard(
        self,
        container_name: str,
        challenge: Challenge,
    ) -> dict[str, Any]:
        """
        Spawn a standard challenge container with no network access.

        Args:
            container_name: Unique name for the container
            challenge: Challenge model instance

        Returns:
            Container info dictionary
        """
        image = challenge.docker_image or self.DEFAULT_IMAGES[ChallengeSubtype.STANDARD]

        # Pull image if needed
        self._pull_image_if_needed(image)

        container = self.docker_client.containers.run(
            image=image,
            name=container_name,
            network="none",  # No network access for isolation
            detach=True,
            mem_limit=self.MEMORY_LIMITS[ChallengeSubtype.STANDARD],
            cpu_quota=50000,  # 50% of one CPU core
            labels={
                "cerberus.subtype": ChallengeSubtype.STANDARD,
                "cerberus.challenge_id": str(challenge.id),
                "cerberus.managed": "true",
            },
        )

        return {
            "container_id": container.id,
            "ip_address": None,  # No network = no IP
            "port_mappings": {},
            "metadata": {
                "image": image,
                "network_mode": "none",
            },
        }

    async def _spawn_blockchain(
        self,
        container_name: str,
        challenge: Challenge,
    ) -> dict[str, Any]:
        """
        Spawn a blockchain challenge with Ganache CLI.

        Generates a deterministic private key and injects it into return data.

        Args:
            container_name: Unique name for the container
            challenge: Challenge model instance

        Returns:
            Container info dictionary with private key
        """
        image = challenge.docker_image or self.DEFAULT_IMAGES[ChallengeSubtype.BLOCKCHAIN]

        # Generate deterministic private key for this instance
        private_key = "0x" + secrets.token_hex(32)

        # Pull image if needed
        self._pull_image_if_needed(image)

        container = self.docker_client.containers.run(
            image=image,
            name=container_name,
            detach=True,
            ports={"8545/tcp": None},  # Expose JSON-RPC port dynamically
            mem_limit=self.MEMORY_LIMITS[ChallengeSubtype.BLOCKCHAIN],
            cpu_quota=50000,
            command=[
                "--deterministic",
                "--accounts", "10",
                "--host", "0.0.0.0",
                "--port", "8545",
                "--gasLimit", "8000000",
                "--gasPrice", "20000000000",
            ],
            labels={
                "cerberus.subtype": ChallengeSubtype.BLOCKCHAIN,
                "cerberus.challenge_id": str(challenge.id),
                "cerberus.managed": "true",
            },
        )

        # Get assigned port
        container.reload()
        port_bindings = container.ports.get("8545/tcp", [])
        host_port = port_bindings[0]["HostPort"] if port_bindings else None

        return {
            "container_id": container.id,
            "ip_address": "127.0.0.1",  # Localhost for blockchain RPC
            "port_mappings": {"8545": host_port} if host_port else {},
            "metadata": {
                "image": image,
                "private_key": private_key,
                "rpc_port": host_port,
                "rpc_url": f"http://127.0.0.1:{host_port}" if host_port else None,
            },
        }

    async def _spawn_ai(
        self,
        container_name: str,
        challenge: Challenge,
    ) -> dict[str, Any]:
        """
        Spawn an AI challenge with HuggingFace Transformers.

        Runs with strict 512MB memory limit as per requirements.

        Args:
            container_name: Unique name for the container
            challenge: Challenge model instance

        Returns:
            Container info dictionary
        """
        image = challenge.docker_image or self.DEFAULT_IMAGES[ChallengeSubtype.AI]

        # Pull image if needed
        self._pull_image_if_needed(image)

        container = self.docker_client.containers.run(
            image=image,
            name=container_name,
            detach=True,
            # Strict 512MB memory limit as required
            mem_limit=self.MEMORY_LIMITS[ChallengeSubtype.AI],
            memswap_limit=self.MEMORY_LIMITS[ChallengeSubtype.AI],  # No swap
            cpu_quota=100000,  # 100% of one CPU core
            labels={
                "cerberus.subtype": ChallengeSubtype.AI,
                "cerberus.challenge_id": str(challenge.id),
                "cerberus.managed": "true",
            },
            environment={
                "TRANSFORMERS_CACHE": "/tmp/transformers",
                "HF_HOME": "/tmp/huggingface",
            },
        )

        return {
            "container_id": container.id,
            "ip_address": None,
            "port_mappings": {},
            "metadata": {
                "image": image,
                "memory_limit_mb": 512,
                "memory_swap_limit_mb": 512,
            },
        }

    async def _spawn_cloud(
        self,
        container_name: str,
        challenge: Challenge,
    ) -> dict[str, Any]:
        """
        Spawn a cloud challenge with LocalStack.

        Simulates AWS services locally for cloud security challenges.

        Args:
            container_name: Unique name for the container
            challenge: Challenge model instance

        Returns:
            Container info dictionary
        """
        image = challenge.docker_image or self.DEFAULT_IMAGES[ChallengeSubtype.CLOUD]

        # Pull image if needed
        self._pull_image_if_needed(image)

        container = self.docker_client.containers.run(
            image=image,
            name=container_name,
            detach=True,
            ports={
                "4566/tcp": None,  # LocalStack edge port
                "4510-4559/tcp": None,  # External service ports
            },
            mem_limit=self.MEMORY_LIMITS[ChallengeSubtype.CLOUD],
            cpu_quota=75000,  # 75% of one CPU core
            environment={
                "SERVICES": "s3,lambda,iam,ec2,rds",  # Common CTF services
                "DEFAULT_REGION": "us-east-1",
                "EDGE_PORT": "4566",
            },
            labels={
                "cerberus.subtype": ChallengeSubtype.CLOUD,
                "cerberus.challenge_id": str(challenge.id),
                "cerberus.managed": "true",
            },
        )

        # Get assigned ports
        container.reload()
        edge_bindings = container.ports.get("4566/tcp", [])
        edge_port = edge_bindings[0]["HostPort"] if edge_bindings else None

        return {
            "container_id": container.id,
            "ip_address": "127.0.0.1",
            "port_mappings": {"4566": edge_port} if edge_port else {},
            "metadata": {
                "image": image,
                "edge_port": edge_port,
                "endpoint_url": f"http://127.0.0.1:{edge_port}" if edge_port else None,
            },
        }

    def _pull_image_if_needed(self, image: str) -> None:
        """
        Pull Docker image if not already present.

        Args:
            image: Docker image name/tag
        """
        try:
            self.docker_client.images.get(image)
            logger.debug(f"Image {image} already exists locally")
        except NotFound:
            logger.info(f"Pulling image {image}...")
            self.docker_client.images.pull(image)
            logger.info(f"Image {image} pulled successfully")

    async def _get_active_instance(
        self,
        user_id: uuid.UUID,
        challenge_id: uuid.UUID,
        db_session: AsyncSession,
    ) -> DynamicInstance | None:
        """
        Check if user has an active instance for this challenge.

        Args:
            user_id: User UUID
            challenge_id: Challenge UUID
            db_session: Database session

        Returns:
            Existing instance if active, None otherwise
        """
        result = await db_session.execute(
            select(DynamicInstance).where(
                DynamicInstance.user_id == user_id,
                DynamicInstance.challenge_id == challenge_id,
                DynamicInstance.status == ContainerStatus.RUNNING,
            )
        )
        instance = result.scalar_one_or_none()

        if instance and instance.expires_at and instance.expires_at > datetime.now(timezone.utc):
            # Update last accessed time
            instance.last_accessed_at = datetime.now(timezone.utc)
            await db_session.commit()
            return instance

        return None

    async def stop_instance(
        self,
        instance_id: uuid.UUID,
        db_session: AsyncSession,
    ) -> bool:
        """
        Stop and remove a container instance.

        Args:
            instance_id: Instance UUID
            db_session: Database session

        Returns:
            True if stopped successfully
        """
        result = await db_session.execute(
            select(DynamicInstance).where(DynamicInstance.id == instance_id)
        )
        instance = result.scalar_one_or_none()

        if not instance:
            logger.warning(f"Instance {instance_id} not found")
            return False

        if instance.active_container_id:
            try:
                container = self.docker_client.containers.get(instance.active_container_id)
                container.stop(timeout=10)
                container.remove(force=True)
                logger.info(f"Stopped and removed container {instance.active_container_id}")
            except NotFound:
                logger.warning(f"Container {instance.active_container_id} already removed")
            except Exception as e:
                logger.error(f"Error stopping container: {e}")

        instance.status = ContainerStatus.STOPPED
        instance.active_container_id = None
        await db_session.commit()

        return True

    async def cleanup_expired_instances(self, db_session: AsyncSession) -> int:
        """
        Cleanup expired instances (running longer than 60 minutes).

        Args:
            db_session: Database session

        Returns:
            Number of instances cleaned up
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(
            minutes=self.DEFAULT_TTL_MINUTES
        )

        result = await db_session.execute(
            select(DynamicInstance).where(
                DynamicInstance.status == ContainerStatus.RUNNING,
                DynamicInstance.expires_at < datetime.now(timezone.utc),
            )
        )
        expired_instances = result.scalars().all()

        cleaned_count = 0
        for instance in expired_instances:
            try:
                await self.stop_instance(instance.id, db_session)
                cleaned_count += 1
                logger.info(f"Cleaned up expired instance {instance.id}")
            except Exception as e:
                logger.error(f"Failed to cleanup instance {instance.id}: {e}")

        return cleaned_count

    async def start_cleanup_task(self, db_session_factory) -> None:
        """
        Start background task for periodic cleanup of expired instances.

        Args:
            db_session_factory: Factory function to create database sessions
        """
        if self._cleanup_task and not self._cleanup_task.done():
            logger.warning("Cleanup task already running")
            return

        self._cleanup_task = asyncio.create_task(
            self._cleanup_loop(db_session_factory)
        )
        logger.info("Started container cleanup background task")

    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped container cleanup background task")

    async def _cleanup_loop(self, db_session_factory) -> None:
        """
        Background loop for periodic cleanup.

        Args:
            db_session_factory: Factory function to create database sessions
        """
        settings = get_settings()
        interval = getattr(settings, "instance_cleanup_interval", 300)  # 5 minutes default

        while True:
            try:
                async with db_session_factory() as session:
                    cleaned = await self.cleanup_expired_instances(session)
                    if cleaned > 0:
                        logger.info(f"Cleanup completed: {cleaned} instances removed")
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

            await asyncio.sleep(interval)


# Global orchestrator instance
_orchestrator: ContainerOrchestrator | None = None


def get_orchestrator() -> ContainerOrchestrator:
    """Get or create the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ContainerOrchestrator()
    return _orchestrator


def reset_orchestrator() -> None:
    """Reset the global orchestrator (useful for testing)."""
    global _orchestrator
    _orchestrator = None
