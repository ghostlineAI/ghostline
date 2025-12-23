"""
Exported book model for tracking generated manuscripts.
"""

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ExportFormat(enum.Enum):
    """Supported export formats."""

    PDF = "pdf"
    DOCX = "docx"
    EPUB = "epub"
    MARKDOWN = "markdown"
    HTML = "html"


class ExportedBook(Base):
    """Exported book model for tracking generated files."""

    __tablename__ = "exported_books"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)

    format = Column(Enum(ExportFormat), nullable=False)
    version = Column(Integer, nullable=False)  # Version number for this export

    # File information
    file_name = Column(String(500), nullable=False)
    s3_key = Column(String(1000), nullable=False)
    file_size_bytes = Column(Integer)

    # Export metadata
    title = Column(String(500), nullable=False)
    subtitle = Column(String(500))
    author_name = Column(String(255))

    # Signed URL expiration tracking
    signed_url = Column(Text)
    signed_url_expires_at = Column(DateTime(timezone=True))

    # Token cost for this export
    token_cost = Column(Integer, default=0)

    # Export options used (as JSON)
    export_options = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    project = relationship("Project", back_populates="exported_books")
