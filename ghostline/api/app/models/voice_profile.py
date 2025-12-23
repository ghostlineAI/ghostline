"""
Voice profile model for author voice analysis.
"""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class VoiceProfile(Base):
    """Voice profile model for author voice analysis."""

    __tablename__ = "voice_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Voice characteristics
    tone = Column(String(100))  # formal, casual, academic, conversational
    style = Column(String(100))  # descriptive, analytical, narrative, persuasive

    # Writing patterns
    avg_sentence_length = Column(Float)
    vocabulary_complexity = Column(Float)  # 0-1 scale

    # Common phrases and patterns
    common_phrases = Column(ARRAY(String))
    sentence_starters = Column(ARRAY(String))
    transition_words = Column(ARRAY(String))

    # Voice embedding (averaged from source materials)
    voice_embedding = Column(Vector(1536))

    # Stylistic elements
    stylistic_elements = Column(
        JSON, default=dict
    )  # punctuation patterns, paragraph structure, etc.

    # Similarity threshold
    similarity_threshold = Column(Float, default=0.88)

    # Project
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, unique=True
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="voice_profile")
