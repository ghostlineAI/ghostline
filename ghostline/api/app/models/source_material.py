"""
Source material model for uploaded content.
"""

import enum
import uuid

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.types import GUID


class MaterialType(enum.Enum):
    """Source material type enumeration."""

    TEXT = "TEXT"
    PDF = "PDF"
    DOCX = "DOCX"
    AUDIO = "AUDIO"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    MARKDOWN = "MARKDOWN"
    HTML = "HTML"
    NOTE = "NOTE"  # Rich text notes created in-app
    VOICE_MEMO = "VOICE_MEMO"  # Voice recordings made in-app
    OTHER = "OTHER"


class ProcessingStatus(enum.Enum):
    """Processing status enumeration."""

    UPLOADING = "UPLOADING"
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    READY = "READY"  # Fully processed and ready for use


class SourceMaterial(Base):
    """Source material model for uploaded content."""

    __tablename__ = "source_materials"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    filename = Column(String(500), nullable=False)
    material_type = Column(Enum(MaterialType), nullable=False)
    file_size = Column(Integer)  # in bytes
    mime_type = Column(String(100))

    # S3 storage
    s3_bucket = Column(String(255), nullable=False)
    s3_key = Column(String(500), nullable=False)
    s3_url = Column(String(1000))

    # Processing
    processing_status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    processing_error = Column(Text)
    processed_at = Column(DateTime(timezone=True))

    # Extracted content
    extracted_text = Column(Text)
    extracted_content = Column(Text)  # Alias for some code paths
    word_count = Column(Integer)
    page_count = Column(Integer)

    # Local storage path (for local dev mode)
    local_path = Column(String(1000), nullable=True)

    # Metadata
    file_metadata = Column(JSON, default=dict)

    # Project
    project_id = Column(GUID(), ForeignKey("projects.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="source_materials")
    chunks = relationship(
        "ContentChunk", back_populates="source_material", cascade="all, delete-orphan"
    )
