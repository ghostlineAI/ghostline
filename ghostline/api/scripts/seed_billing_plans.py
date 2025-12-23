"""Script to seed billing plans in the database."""

import sys
import uuid
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import SessionLocal
from app.models.billing_plan import BillingPlan


def seed_billing_plans():
    """Seed the database with default billing plans."""
    db = SessionLocal()

    try:
        # Check if plans already exist
        existing_plans = db.query(BillingPlan).count()
        if existing_plans > 0:
            print(
                f"Billing plans already exist ({existing_plans} found). Skipping seed."
            )
            return

        # Define billing plans
        plans = [
            {
                "id": str(uuid.uuid4()),
                "name": "basic",
                "display_name": "Basic",
                "description": "Perfect for getting started with AI-powered book writing",
                "monthly_token_quota": 100000,
                "price_cents": 0,
                "features": "100k tokens/month, Basic support, 1 active project",
                "is_active": True,
            },
            {
                "id": str(uuid.uuid4()),
                "name": "premium",
                "display_name": "Premium",
                "description": "For serious authors who need more AI power",
                "monthly_token_quota": 500000,
                "price_cents": 4900,  # $49/month
                "features": "500k tokens/month, Priority support, 5 active projects, Advanced QA",
                "is_active": True,
            },
            {
                "id": str(uuid.uuid4()),
                "name": "pro",
                "display_name": "Professional",
                "description": "For professional writers and publishing teams",
                "monthly_token_quota": 2000000,
                "price_cents": 14900,  # $149/month
                "features": "2M tokens/month, Dedicated support, Unlimited projects, Custom voice profiles, Team collaboration",
                "is_active": True,
            },
        ]

        # Create billing plans
        for plan_data in plans:
            plan = BillingPlan(**plan_data)
            db.add(plan)
            print(f"Created billing plan: {plan.display_name}")

        db.commit()
        print("Successfully seeded billing plans!")

    except Exception as e:
        print(f"Error seeding billing plans: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_billing_plans()
