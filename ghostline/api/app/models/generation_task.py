"""
Generation task model for agent workflows.
"""

import enum
import uuid

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class TaskType(enum.Enum):
    """Task type enumeration."""

    VOICE_ANALYSIS = "voice_analysis"
    OUTLINE_GENERATION = "outline_generation"
    CHAPTER_GENERATION = "chapter_generation"
    CHAPTER_REVISION = "chapter_revision"
    CONSISTENCY_CHECK = "consistency_check"
    SAFETY_CHECK = "safety_check"
    FINAL_COMPILATION = "final_compilation"


class TaskStatus(enum.Enum):
    """Task status enumeration."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"  # Waiting for user input (e.g., outline approval)
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GenerationTask(Base):
    """Generation task model for agent workflows."""

    __tablename__ = "generation_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type = Column(Enum(TaskType), nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)

    # Task details
    agent_name = Column(String(100))  # Which agent is handling this
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    error_message = Column(Text)

    # Metrics (token_usage is JSON to store detailed breakdown)
    token_usage = Column(JSON, default=dict)
    estimated_cost = Column(Float, default=0.0)
    execution_time = Column(Integer)  # in seconds

    # Progress tracking
    progress = Column(Integer, default=0)  # 0-100
    current_step = Column(String(500))

    # Retry logic
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Project and chapter references
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id"))

    # Celery task ID
    celery_task_id = Column(String(255))
    
    # LangGraph workflow state (for durable pause/resume)
    workflow_state = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Entity tracking (what was created/updated by this task)
    output_entity_type = Column(String(50))  # e.g., "book_outline", "chapter_revision"
    output_entity_id = Column(UUID(as_uuid=True))  # ID of the created entity

    # Relationships
    project = relationship("Project", back_populates="generation_tasks")
    token_transactions = relationship(
        "TokenTransaction", back_populates="generation_task"
    )
    chapter = relationship("Chapter")
