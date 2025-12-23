"""
QA finding model for tracking issues found during quality assurance.
"""

import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class FindingType(enum.Enum):
    """Types of QA findings."""

    NAME_INCONSISTENCY = "name_inconsistency"
    TIMELINE_ERROR = "timeline_error"
    TONE_DRIFT = "tone_drift"
    FACTUAL_ERROR = "factual_error"
    HALLUCINATION = "hallucination"
    STYLE_DEVIATION = "style_deviation"
    CONTINUITY_ERROR = "continuity_error"


class FindingStatus(enum.Enum):
    """Status of a QA finding."""

    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    WAIVED = "waived"


class QaFinding(Base):
    """QA finding model for tracking issues."""

    __tablename__ = "qa_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_revision_id = Column(
        UUID(as_uuid=True), ForeignKey("chapter_revisions.id"), nullable=False
    )

    finding_type = Column(Enum(FindingType), nullable=False)
    severity = Column(String(20), nullable=False)  # low, medium, high, critical

    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)

    # Location in the text where the issue was found
    start_position = Column(Integer)
    end_position = Column(Integer)
    context = Column(Text)  # Surrounding text for context

    # Suggested fix from the AI
    suggested_fix = Column(Text)

    status = Column(Enum(FindingStatus), default=FindingStatus.OPEN)
    is_blocking = Column(Boolean, default=False)  # Whether this blocks export

    # User's response to the finding
    user_comment = Column(Text)
    resolved_by_revision_id = Column(
        UUID(as_uuid=True), ForeignKey("chapter_revisions.id")
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))

    # Relationships
    chapter_revision = relationship(
        "ChapterRevision",
        foreign_keys=[chapter_revision_id],
        back_populates="qa_findings",
    )
    resolved_by_revision = relationship(
        "ChapterRevision", foreign_keys=[resolved_by_revision_id]
    )
