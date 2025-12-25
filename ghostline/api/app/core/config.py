"""
Application configuration settings.
"""

import os
import json
from typing import Any

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Project Info
    PROJECT_NAME: str = "GhostLine API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local")

    # Security
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "local-dev-secret-key-not-for-production"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Auth bypass for local development (no login required)
    AUTH_DISABLED: bool = os.getenv("AUTH_DISABLED", "true").lower() == "true"

    # Database - Local PostgreSQL via docker-compose
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://ghostline:ghostline@localhost:5432/ghostline"
    )

    # Redis - Local via docker-compose
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Local file storage (instead of S3 for local dev)
    USE_LOCAL_STORAGE: bool = os.getenv("USE_LOCAL_STORAGE", "true").lower() == "true"
    LOCAL_STORAGE_PATH: str = os.getenv("LOCAL_STORAGE_PATH", "./uploads")

    # AWS - Optional, leave empty for local dev
    AWS_REGION: str = os.getenv("AWS_REGION", "us-west-2")
    AWS_ACCESS_KEY_ID: str | None = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")

    # S3 Buckets - Only used if USE_LOCAL_STORAGE is False
    S3_SOURCE_MATERIALS_BUCKET: str = os.getenv(
        "S3_SOURCE_MATERIALS_BUCKET", 
        "ghostline-local-materials"
    )
    S3_OUTPUTS_BUCKET: str = os.getenv(
        "S3_OUTPUTS_BUCKET",
        "ghostline-local-outputs"
    )

    # CORS - Parse safely from environment
    @property
    def BACKEND_CORS_ORIGINS(self) -> list[str]:
        """Parse CORS origins from environment variable safely."""
        # Default origins if no env var is set
        default_origins = [
            "http://localhost:3000",
            "https://dev.ghostline.ai",
            "https://d2thhts2eu7se8.cloudfront.net",
        ]
        
        # Get env var
        raw = os.getenv("BACKEND_CORS_ORIGINS")
        if not raw:
            return default_origins

        raw = raw.strip()
        if not raw:
            return default_origins
            
        # Try to parse as JSON first
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(origin).strip() for origin in parsed if origin]
        except (json.JSONDecodeError, ValueError):
            pass

        # Handle common non-JSON bracket formats seen in .env files:
        # - [http://localhost:3000]
        # - ['http://localhost:3000', 'http://localhost:3001']
        # - [ "http://localhost:3000" ]
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            if not inner:
                return default_origins
            # Split on commas (if any) and strip whitespace/quotes
            parts = [
                part.strip().strip('"').strip("'")
                for part in inner.split(",")
                if part.strip()
            ]
            parts = [p for p in parts if p]
            if parts:
                return parts
            
        # Fall back to comma-separated
        if "," in raw:
            return [origin.strip() for origin in raw.split(",") if origin.strip()]
            
        # Single origin
        return [raw]
            
        # (unreachable)

    # AI Models (for future use)
    CLAUDE_MODEL: str = "claude-3-haiku-20240307"
    GPT_MODEL: str = "gpt-4o"

    class Config:
        """Pydantic config."""

        case_sensitive = True
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields


settings = Settings()
