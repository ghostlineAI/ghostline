"""
Chapter model for book content.
"""

import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Chapter(Base):
    """Chapter model for book content."""

    __tablename__ = "chapters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    order = Column(Integer, nullable=False)  # Chapter number/order

    # Content
    content = Column(Text)  # Markdown format
    word_count = Column(Integer, default=0)

    # Outline
    outline = Column(Text)  # Chapter outline/summary
    key_points = Column(JSON, default=list)  # List of key points

    # Version tracking
    version = Column(Integer, default=1)
    is_final = Column(Boolean, default=False)

    # Foreign keys
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    book_outline_id = Column(UUID(as_uuid=True), ForeignKey("book_outlines.id"))

    # Status tracking
    status = Column(String(50), default="draft")  # draft, reviewing, approved

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="chapters")
    book_outline = relationship("BookOutline", back_populates="chapters")
    revisions = relationship(
        "ChapterRevision", back_populates="chapter", cascade="all, delete-orphan"
    )
