"""
Billing plan model for subscription tiers.
"""

import uuid

from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class BillingPlan(Base):
    """Billing plan model for subscription tiers."""

    __tablename__ = "billing_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False, unique=True)  # Basic, Premium, Pro
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    monthly_token_quota = Column(Integer, nullable=False)
    price_cents = Column(Integer, nullable=False)  # Price in cents for Stripe
    stripe_price_id = Column(String(255))  # Stripe Price ID for subscription
    features = Column(Text)  # JSON string of feature flags
    is_active = Column(Boolean, default=True)

    # Relationships
    users = relationship("User", back_populates="billing_plan")
