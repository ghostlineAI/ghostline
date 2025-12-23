"""
Notification model for user notifications.
"""

import enum
import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class NotificationType(enum.Enum):
    """Types of notifications."""

    UPLOAD_COMPLETE = "upload_complete"
    OUTLINE_READY = "outline_ready"
    CHAPTER_DRAFT_READY = "chapter_draft_ready"
    QA_COMPLETE = "qa_complete"
    EXPORT_READY = "export_ready"
    BILLING_ALERT = "billing_alert"
    TOKEN_LOW = "token_low"
    SYSTEM_ANNOUNCEMENT = "system_announcement"


class NotificationChannel(enum.Enum):
    """Notification delivery channels."""

    IN_APP = "in_app"
    EMAIL = "email"
    WEBSOCKET = "websocket"


class Notification(Base):
    """Notification model for user alerts."""

    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))

    notification_type = Column(Enum(NotificationType), nullable=False)
    channel = Column(Enum(NotificationChannel), nullable=False)

    # Notification content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON)  # Additional structured data

    # Deep link to relevant content
    link_url = Column(String(1000))
    link_text = Column(String(255))

    # Tracking
    is_read = Column(Boolean, default=False)
    is_sent = Column(Boolean, default=False)

    # For email/SMS channels
    external_id = Column(String(255))  # e.g., SES message ID
    notification_metadata = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True))
    read_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="notifications")
    project = relationship("Project", back_populates="notifications")
