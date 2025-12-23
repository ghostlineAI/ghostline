from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BillingInfo(BaseModel):
    plan_name: str
    plan_id: str
    monthly_tokens: int
    tokens_used: int
    tokens_remaining: int
    price_per_month: float
    billing_cycle_start: datetime
    billing_cycle_end: datetime


class TokenTransaction(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    project_id: str | None
    tokens: int
    transaction_type: str
    description: str
    created_at: datetime


class TokenUsage(BaseModel):
    transactions: list[TokenTransaction]
    daily_usage: dict[str, int]
    total_usage: int
    period_start: datetime
    period_end: datetime


class PlanUpgrade(BaseModel):
    plan_id: str = Field(..., description="ID of the plan to upgrade to")


class BillingPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    monthly_tokens: int
    price_per_month: float
    features: dict[str, bool]
    is_active: bool
