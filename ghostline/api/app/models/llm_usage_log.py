"""
LLM Usage Log model for granular cost tracking.

Records every LLM API call with detailed metrics for cost analysis.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


# Simple string constants for provider and call type
# (Using strings instead of enums to avoid SQLAlchemy enum creation issues)
class LLMProvider:
    """LLM provider constants."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LOCAL = "local"


class CallType:
    """Type of LLM call."""
    CHAT = "chat"
    EMBEDDING = "embedding"
    VISION = "vision"


class LLMUsageLog(Base):
    """
    Granular log of every LLM API call.
    
    Enables cost analysis at any aggregation level:
    - Per call
    - Per agent
    - Per chapter
    - Per project/run
    - Per model
    - Per provider
    """
    
    __tablename__ = "llm_usage_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # ─────────────────────────────────────────────────────────────────
    # Context: What triggered this call
    # ─────────────────────────────────────────────────────────────────
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("generation_tasks.id"), nullable=True, index=True)
    workflow_run_id = Column(String(255), nullable=True, index=True)  # LangGraph run ID
    
    # Which chapter (if applicable)
    chapter_number = Column(Integer, nullable=True)
    
    # ─────────────────────────────────────────────────────────────────
    # Agent info: Who made this call
    # ─────────────────────────────────────────────────────────────────
    agent_name = Column(String(100), nullable=False, index=True)
    agent_role = Column(String(50), nullable=True)  # drafter, editor, fact_checker, etc.
    
    # ─────────────────────────────────────────────────────────────────
    # Model info: What model was used
    # ─────────────────────────────────────────────────────────────────
    provider = Column(String(50), nullable=False, index=True)  # anthropic, openai, local
    model = Column(String(100), nullable=False, index=True)
    call_type = Column(String(50), default="chat", index=True)  # chat, embedding, vision
    
    # Was this a fallback call (e.g., Anthropic -> OpenAI)?
    is_fallback = Column(Boolean, default=False)
    fallback_reason = Column(String(255), nullable=True)
    
    # ─────────────────────────────────────────────────────────────────
    # Token usage
    # ─────────────────────────────────────────────────────────────────
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # For embeddings
    embedding_dimensions = Column(Integer, nullable=True)
    
    # ─────────────────────────────────────────────────────────────────
    # Cost (in USD)
    # ─────────────────────────────────────────────────────────────────
    input_cost = Column(Float, default=0.0)
    output_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    
    # Pricing used for calculation (for auditability)
    input_price_per_1k = Column(Float, nullable=True)  # $/1K tokens
    output_price_per_1k = Column(Float, nullable=True)  # $/1K tokens
    
    # ─────────────────────────────────────────────────────────────────
    # Performance
    # ─────────────────────────────────────────────────────────────────
    duration_ms = Column(Integer, default=0)
    
    # ─────────────────────────────────────────────────────────────────
    # Request/Response metadata (for debugging)
    # ─────────────────────────────────────────────────────────────────
    prompt_preview = Column(Text, nullable=True)  # First 500 chars of prompt
    response_preview = Column(Text, nullable=True)  # First 500 chars of response
    
    # Was the call successful?
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Additional metadata (e.g., temperature, max_tokens, etc.)
    extra_data = Column(JSON, default=dict)
    
    # ─────────────────────────────────────────────────────────────────
    # Timestamps
    # ─────────────────────────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # ─────────────────────────────────────────────────────────────────
    # Relationships
    # ─────────────────────────────────────────────────────────────────
    project = relationship("Project", backref="llm_usage_logs")
    task = relationship("GenerationTask", backref="llm_usage_logs")
    
    def __repr__(self):
        return (
            f"<LLMUsageLog(id={self.id}, agent={self.agent_name}, "
            f"model={self.model}, tokens={self.total_tokens}, cost=${self.total_cost:.4f})>"
        )

