"""
Token transaction model for tracking token usage and credits.
"""

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class TransactionType(enum.Enum):
    """Types of token transactions."""

    CREDIT = "credit"  # Adding tokens (purchase, monthly quota)
    DEBIT = "debit"  # Using tokens (generation, export)


class TokenTransaction(Base):
    """Token transaction model for tracking usage."""

    __tablename__ = "token_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    generation_task_id = Column(UUID(as_uuid=True), ForeignKey("generation_tasks.id"))

    transaction_type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Integer, nullable=False)  # Positive for credit, negative for debit
    balance_after = Column(Integer, nullable=False)  # User's balance after transaction

    description = Column(Text, nullable=False)
    transaction_metadata = Column(Text)  # JSON string for additional data

    stripe_charge_id = Column(String(255))  # For purchases

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="token_transactions")
    project = relationship("Project", back_populates="token_transactions")
    generation_task = relationship(
        "GenerationTask", back_populates="token_transactions"
    )
