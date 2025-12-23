from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.api import deps
from app.models.billing_plan import BillingPlan
from app.models.token_transaction import TokenTransaction
from app.models.user import User
from app.schemas.billing import BillingInfo, PlanUpgrade, TokenUsage

router = APIRouter()


@router.get("/info", response_model=BillingInfo)
def get_billing_info(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Get current billing information for the user."""
    # Get user's current plan
    plan = (
        db.query(BillingPlan)
        .filter(BillingPlan.id == current_user.billing_plan_id)
        .first()
    )

    if not plan:
        # Default to basic plan
        plan = db.query(BillingPlan).filter(BillingPlan.name == "Basic").first()

    # Calculate current month usage
    start_of_month = datetime.utcnow().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    tokens_used = (
        db.query(func.sum(TokenTransaction.tokens))
        .filter(
            and_(
                TokenTransaction.user_id == current_user.id,
                TokenTransaction.created_at >= start_of_month,
                TokenTransaction.transaction_type == "usage",
            )
        )
        .scalar()
        or 0
    )

    tokens_remaining = plan.monthly_tokens - tokens_used

    return {
        "plan_name": plan.name,
        "plan_id": plan.id,
        "monthly_tokens": plan.monthly_tokens,
        "tokens_used": tokens_used,
        "tokens_remaining": max(0, tokens_remaining),
        "price_per_month": plan.price_per_month,
        "billing_cycle_start": start_of_month,
        "billing_cycle_end": (start_of_month + timedelta(days=32)).replace(day=1)
        - timedelta(seconds=1),
    }


@router.get("/usage", response_model=TokenUsage)
def get_token_usage(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    days: int = 30,
):
    """Get detailed token usage history."""
    start_date = datetime.utcnow() - timedelta(days=days)

    transactions = (
        db.query(TokenTransaction)
        .filter(
            and_(
                TokenTransaction.user_id == current_user.id,
                TokenTransaction.created_at >= start_date,
            )
        )
        .order_by(TokenTransaction.created_at.desc())
        .all()
    )

    # Calculate daily usage
    daily_usage = {}
    for transaction in transactions:
        date_key = transaction.created_at.date().isoformat()
        if date_key not in daily_usage:
            daily_usage[date_key] = 0
        if transaction.transaction_type == "usage":
            daily_usage[date_key] += transaction.tokens

    return {
        "transactions": transactions,
        "daily_usage": daily_usage,
        "total_usage": sum(
            t.tokens for t in transactions if t.transaction_type == "usage"
        ),
        "period_start": start_date,
        "period_end": datetime.utcnow(),
    }


@router.post("/upgrade-plan")
def upgrade_plan(
    plan_upgrade: PlanUpgrade,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Upgrade to a different billing plan."""
    # Get the new plan
    new_plan = (
        db.query(BillingPlan).filter(BillingPlan.id == plan_upgrade.plan_id).first()
    )

    if not new_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        )

    # Update user's plan
    current_user.billing_plan_id = new_plan.id

    # Add transaction for plan change
    transaction = TokenTransaction(
        user_id=current_user.id,
        project_id=None,
        tokens=new_plan.monthly_tokens,
        transaction_type="credit",
        description=f"Upgraded to {new_plan.name} plan",
        metadata={
            "plan_id": new_plan.id,
            "plan_name": new_plan.name,
            "upgrade_date": datetime.utcnow().isoformat(),
        },
    )

    db.add(transaction)
    db.commit()

    return {
        "message": f"Successfully upgraded to {new_plan.name} plan",
        "new_plan": new_plan,
        "tokens_credited": new_plan.monthly_tokens,
    }


@router.get("/plans", response_model=list[dict])
def list_billing_plans(
    db: Session = Depends(deps.get_db),
):
    """List all available billing plans."""
    plans = (
        db.query(BillingPlan)
        .filter(BillingPlan.is_active)
        .order_by(BillingPlan.price_per_month)
        .all()
    )

    return plans
