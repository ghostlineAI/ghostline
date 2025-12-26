"""
Voice profile model for author voice analysis.

Stores both:
1. Numeric stylometry metrics for strict voice similarity measurement
2. OpenAI embeddings for semantic voice matching
3. LLM-extracted style descriptions for prompt context
"""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.types import GUID


class VoiceProfile(Base):
    """Voice profile model for author voice analysis with numeric metrics."""

    __tablename__ = "voice_profiles"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # From migration: name and description
    name = Column(String(255), nullable=True)  # e.g., "Author's Primary Voice"
    description = Column(Text, nullable=True)
    sample_text = Column(Text, nullable=True)  # Representative sample
    style_attributes = Column(JSON, nullable=True)  # From migration

    # Voice characteristics (categorical)
    tone = Column(String(100), nullable=True)  # formal, casual, academic, conversational
    style = Column(String(100), nullable=True)  # descriptive, analytical, narrative, persuasive

    # =========================================================================
    # NUMERIC STYLOMETRY METRICS (for strict voice similarity)
    # =========================================================================
    
    # Sentence-level metrics
    avg_sentence_length = Column(Float, nullable=True)  # Average words per sentence
    sentence_length_std = Column(Float, nullable=True)  # Sentence length variation
    
    # Word-level metrics
    avg_word_length = Column(Float, nullable=True)  # Average characters per word
    vocabulary_complexity = Column(Float, nullable=True)  # Type-token ratio (0-1)
    vocabulary_richness = Column(Float, nullable=True)  # Hapax legomena ratio
    
    # Punctuation metrics
    punctuation_density = Column(Float, nullable=True)  # Punctuation per 100 words
    question_ratio = Column(Float, nullable=True)  # Questions per sentence
    exclamation_ratio = Column(Float, nullable=True)  # Exclamations per sentence
    
    # Paragraph metrics
    avg_paragraph_length = Column(Float, nullable=True)  # Sentences per paragraph

    # Common phrases and patterns (for pattern matching)
    # NOTE: Tests run against SQLite by default. Use JSON fallback so metadata.create_all works
    # without Postgres ARRAY support.
    common_phrases = Column(ARRAY(String).with_variant(JSON(), "sqlite"), nullable=True)
    sentence_starters = Column(ARRAY(String).with_variant(JSON(), "sqlite"), nullable=True)
    transition_words = Column(ARRAY(String).with_variant(JSON(), "sqlite"), nullable=True)

    # Voice embedding (OpenAI text-embedding-3-small, 1536 dimensions)
    # NOTE: SQLite fallback so tests can run without pgvector.
    voice_embedding = Column(Vector(1536).with_variant(JSON(), "sqlite"), nullable=True)

    # Stylistic elements (detailed patterns as JSON)
    stylistic_elements = Column(JSON, default=dict)
    
    # Style description for LLM prompts
    style_description = Column(Text, nullable=True)

    # =========================================================================
    # VOICE MATCHING CONFIGURATION
    # =========================================================================
    
    # Minimum similarity score required (0.0 - 1.0)
    # Content below this threshold will be flagged/rejected
    similarity_threshold = Column(Float, default=0.85)
    
    # Weight for embedding similarity vs stylometry (0=stylometry only, 1=embedding only)
    embedding_weight = Column(Float, default=0.4)
    
    # Is this the active voice profile for the project?
    is_active = Column(Boolean, default=True)

    # Project (one-to-one)
    project_id = Column(
        GUID(), ForeignKey("projects.id"), nullable=False, unique=True
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="voice_profile")
