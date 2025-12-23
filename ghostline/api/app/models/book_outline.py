"""
Book outline model for storing the hierarchical structure of a book.
"""

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class OutlineStatus(enum.Enum):
    """Status of a book outline."""

    DRAFT = "draft"
    APPROVED = "approved"
    ARCHIVED = "archived"


class BookOutline(Base):
    """Book outline model for storing the structure."""

    __tablename__ = "book_outlines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)

    title = Column(String(500), nullable=False)
    subtitle = Column(String(500))

    # Hierarchical structure as JSON
    # Format: {"parts": [{"title": "Part 1", "chapters": [{"title": "Chapter 1", "scenes": [...]}]}]}
    structure = Column(Text, nullable=False)

    status = Column(Enum(OutlineStatus), default=OutlineStatus.DRAFT)
    version = Column(Integer, default=1)

    # User notes about the outline
    notes = Column(Text)

    # Token cost for generating this outline
    token_cost = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True))

    # Relationships
    project = relationship("Project", back_populates="book_outlines")
    chapters = relationship(
        "Chapter", back_populates="book_outline", cascade="all, delete-orphan"
    )
