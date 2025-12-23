"""
API key model for authentication.
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class APIKey(Base):
    """API key model for authentication."""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    key = Column(String(255), unique=True, index=True, nullable=False)

    # Permissions
    is_active = Column(Boolean, default=True)
    scopes = Column(String(500))  # Comma-separated list of scopes

    # Usage tracking
    last_used_at = Column(DateTime(timezone=True))
    usage_count = Column(Integer, default=0)

    # User
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="api_keys")
