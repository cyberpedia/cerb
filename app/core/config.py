"""
Cerberus - Enterprise CTF Platform Configuration
Pydantic Settings for application configuration
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Cerberus", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    secret_key: str = Field(
        default="change-me-in-production",
        description="Secret key for JWT and encryption",
    )

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/cyberrange",
        description="PostgreSQL async connection URL",
    )
    database_echo: bool = Field(
        default=False, description="Echo SQL queries to stdout"
    )
    database_pool_size: int = Field(default=10, description="Database pool size")
    database_max_overflow: int = Field(
        default=20, description="Database max overflow connections"
    )

    # Security
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="Refresh token expiration in days"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    password_min_length: int = Field(
        default=8, description="Minimum password length"
    )

    # OAuth Providers
    oauth_github_client_id: str | None = Field(
        default=None, description="GitHub OAuth client ID"
    )
    oauth_github_client_secret: str | None = Field(
        default=None, description="GitHub OAuth client secret"
    )
    oauth_google_client_id: str | None = Field(
        default=None, description="Google OAuth client ID"
    )
    oauth_google_client_secret: str | None = Field(
        default=None, description="Google OAuth client secret"
    )

    # CORS
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins",
    )

    # Rate Limiting
    rate_limit_requests: int = Field(
        default=100, description="Rate limit requests per window"
    )
    rate_limit_window: int = Field(
        default=60, description="Rate limit window in seconds"
    )

    # File Upload
    max_upload_size_mb: int = Field(
        default=10, description="Maximum upload size in MB"
    )
    avatar_upload_path: str = Field(
        default="uploads/avatars", description="Avatar upload directory"
    )

    # Docker/Dynamic Instances
    docker_registry: str = Field(
        default="localhost:5000", description="Docker registry URL"
    )
    instance_cleanup_interval: int = Field(
        default=300, description="Instance cleanup interval in seconds"
    )
    default_instance_ttl: int = Field(
        default=3600, description="Default instance TTL in seconds"
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
