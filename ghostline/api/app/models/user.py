"""
User model for authentication and profile management.
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.types import GUID


class User(Base):
    """User model for authentication and profile management."""

    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255))
    hashed_password = Column(String(255), nullable=False)

    # Cognito integration
    cognito_sub = Column(String(255), unique=True, index=True)  # Cognito user ID

    # Profile fields
    bio = Column(Text)
    avatar_url = Column(String(500))

    # Billing
    billing_plan_id = Column(GUID(), ForeignKey("billing_plans.id"))
    token_balance = Column(Integer, default=0)
    stripe_customer_id = Column(String(255), unique=True)

    # Status fields
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    projects = relationship(
        "Project", back_populates="owner", cascade="all, delete-orphan"
    )
    api_keys = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )
    billing_plan = relationship("BillingPlan", back_populates="users")
    token_transactions = relationship(
        "TokenTransaction", back_populates="user", cascade="all, delete-orphan"
    )
    notifications = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
