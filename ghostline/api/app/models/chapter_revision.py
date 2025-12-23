"""
Chapter revision model for version tracking.
"""

import uuid

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ChapterRevision(Base):
    """Chapter revision model for version tracking."""

    __tablename__ = "chapter_revisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(Integer, nullable=False)

    # Content
    content = Column(Text, nullable=False)
    word_count = Column(Integer, default=0)

    # Change tracking
    change_summary = Column(Text)
    change_type = Column(String(50))  # minor, major, rewrite

    # Feedback
    feedback = Column(JSON, default=dict)

    # Chapter
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id"), nullable=False)

    # Created by (could be user or agent)
    created_by = Column(String(100))  # user_id or agent_name

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Similarity and cost tracking
    similarity_score = Column(Float)  # Tone/style similarity to voice profile
    token_cost = Column(Integer, default=0)  # Tokens used for this revision

    # Relationships
    chapter = relationship("Chapter", back_populates="revisions")
    qa_findings = relationship(
        "QaFinding",
        foreign_keys="QaFinding.chapter_revision_id",
        back_populates="chapter_revision",
    )
