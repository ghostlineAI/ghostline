"""
Project model for book projects.
"""

import enum
import uuid

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ProjectStatus(enum.Enum):
    """Project status enumeration."""

    DRAFT = "draft"
    PROCESSING = "processing"
    READY = "ready"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class BookGenre(enum.Enum):
    """Book genre enumeration."""

    FICTION = "fiction"
    NON_FICTION = "non_fiction"
    MEMOIR = "memoir"
    BUSINESS = "business"
    SELF_HELP = "self_help"
    ACADEMIC = "academic"
    TECHNICAL = "technical"
    OTHER = "other"


class Project(Base):
    """Project model for book projects."""

    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    subtitle = Column(String(500))
    description = Column(Text)
    genre = Column(Enum(BookGenre, values_callable=lambda obj: [e.value for e in obj]), default=BookGenre.OTHER)
    target_audience = Column(String(500))

    # Book metadata
    target_page_count = Column(Integer, default=80)
    target_word_count = Column(Integer, default=20000)
    language = Column(String(10), default="en")

    # Status
    status = Column(Enum(ProjectStatus, values_callable=lambda obj: [e.value for e in obj]), default=ProjectStatus.DRAFT)

    # Settings
    settings = Column(JSON, default=dict)

    # Owner
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))

    # Forking support
    forked_from_project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))

    # Relationships
    owner = relationship("User", back_populates="projects")
    source_materials = relationship(
        "SourceMaterial", back_populates="project", cascade="all, delete-orphan"
    )
    chapters = relationship(
        "Chapter",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Chapter.order",
    )
    voice_profile = relationship(
        "VoiceProfile",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan",
    )
    generation_tasks = relationship(
        "GenerationTask", back_populates="project", cascade="all, delete-orphan"
    )
    book_outlines = relationship(
        "BookOutline", back_populates="project", cascade="all, delete-orphan"
    )
    token_transactions = relationship("TokenTransaction", back_populates="project")
    notifications = relationship("Notification", back_populates="project")
    exported_books = relationship(
        "ExportedBook", back_populates="project", cascade="all, delete-orphan"
    )
    forked_from = relationship("Project", remote_side=[id], backref="forks")
