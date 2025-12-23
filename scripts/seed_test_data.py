"""Script to seed test data in the database."""

import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import SessionLocal
from app.models.user import User
from app.models.project import Project, ProjectStatus, BookGenre
from app.models.billing_plan import BillingPlan
from app.services.auth import get_password_hash


def seed_test_data():
    """Seed the database with test data."""
    db = SessionLocal()

    try:
        # Get basic billing plan
        basic_plan = db.query(BillingPlan).filter(BillingPlan.name == "basic").first()
        if not basic_plan:
            print("No billing plans found. Run seed_billing_plans.py first!")
            return

        # Create test user
        test_user = User(
            id=str(uuid.uuid4()),
            email="test@ghostline.ai",
            username="testuser",
            full_name="Test User",
            hashed_password=get_password_hash("testpass123"),
            is_active=True,
            is_verified=True,
            billing_plan_id=basic_plan.id,
            current_token_balance=100000,
            created_at=datetime.utcnow()
        )
        db.add(test_user)
        print("Created test user: test@ghostline.ai")

        # Create test projects
        projects = [
            {
                "id": str(uuid.uuid4()),
                "title": "My Life Story",
                "description": "An autobiography covering my journey from childhood to present day",
                "owner_id": test_user.id,
                "status": ProjectStatus.DRAFT,
                "genre": BookGenre.MEMOIR,
                "created_at": datetime.utcnow()
            },
            {
                "id": str(uuid.uuid4()),
                "title": "The AI Revolution",
                "description": "A comprehensive guide to artificial intelligence and its impact on society",
                "owner_id": test_user.id,
                "status": ProjectStatus.DATA_COLLECTION,
                "genre": BookGenre.TECHNICAL,
                "created_at": datetime.utcnow()
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Building Better Habits",
                "description": "A self-help book about forming positive habits and breaking bad ones",
                "owner_id": test_user.id,
                "status": ProjectStatus.DRAFT,
                "genre": BookGenre.SELF_HELP,
                "created_at": datetime.utcnow()
            }
        ]

        for project_data in projects:
            project = Project(**project_data)
            db.add(project)
            print(f"Created project: {project.title}")

        db.commit()
        print("\nSuccessfully seeded test data!")
        print("Login credentials: test@ghostline.ai / testpass123")

    except Exception as e:
        print(f"Error seeding test data: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_test_data() 