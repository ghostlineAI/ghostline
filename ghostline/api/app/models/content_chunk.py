"""
Content chunk model for vector embeddings and retrieval.

Stores text chunks from source materials with embeddings for RAG retrieval.
Uses OpenAI text-embedding-3-small (1536 dimensions) as the standard.
"""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ContentChunk(Base):
    """Content chunk model for vector embeddings and retrieval."""

    __tablename__ = "content_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Content
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False, default=0)
    word_count = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)  # Made nullable for migration compatibility

    # Position in source document
    start_page = Column(Integer, nullable=True)
    end_page = Column(Integer, nullable=True)
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)

    # Embeddings (1536 dimensions for OpenAI text-embedding-3-small)
    embedding = Column(Vector(1536))
    embedding_model = Column(String(100), default="text-embedding-3-small")

    # Citation tracking for RAG grounding
    source_reference = Column(String(500), nullable=True)  # e.g., "Chapter 3, p.45"
    chunk_metadata = Column("metadata", JSON, nullable=True)  # Additional structured metadata

    # Foreign keys
    source_material_id = Column(
        UUID(as_uuid=True), ForeignKey("source_materials.id"), nullable=False
    )
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    source_material = relationship("SourceMaterial", back_populates="chunks")
    project = relationship("Project", back_populates="content_chunks")
