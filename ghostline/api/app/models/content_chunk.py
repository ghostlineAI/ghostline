"""
Content chunk model for vector embeddings and retrieval.
"""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
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
    token_count = Column(Integer, nullable=False)

    # Position in source
    start_page = Column(Integer)
    end_page = Column(Integer)
    start_char = Column(Integer)
    end_char = Column(Integer)

    # Embeddings (1536 dimensions for OpenAI ada-002)
    embedding = Column(Vector(1536))
    embedding_model = Column(String(100), default="text-embedding-ada-002")

    # Source material
    source_material_id = Column(
        UUID(as_uuid=True), ForeignKey("source_materials.id"), nullable=False
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    source_material = relationship("SourceMaterial", back_populates="chunks")
