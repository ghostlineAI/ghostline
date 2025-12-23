"""
Test project creation with our enum fix against production database
"""
import pytest
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.project import Project, ProjectStatus, BookGenre
from app.models.billing_plan import BillingPlan
import uuid


def test_create_project_with_enum_fix(client, db: Session, auth_headers):
    """Test that project creation works with our enum fix"""
    
    # Ensure we have a billing plan (required for users)
    billing_plan = db.query(BillingPlan).filter_by(name="basic").first()
    if not billing_plan:
        billing_plan = BillingPlan(
            id=str(uuid.uuid4()),
            name="basic",
            display_name="Basic",
            description="Basic plan",
            monthly_token_quota=100000,
            price_cents=0,
            is_active=True
        )
        db.add(billing_plan)
        db.commit()
    
    # Create project with our fixed enum handling
    project_data = {
        "title": "Test Enum Fix Project",
        "genre": "fiction",
        "description": "Testing the enum fix works"
    }
    
    response = client.post(
        "/api/v1/projects/",
        json=project_data,
        headers=auth_headers
    )
    
    # This should now work with our fix!
    assert response.status_code == 200, f"Failed: {response.text}"
    
    data = response.json()
    assert data["title"] == project_data["title"]
    assert data["genre"] == "fiction"  # Should be lowercase
    assert data["status"] == "draft"   # Should be lowercase
    
    # Verify in database
    db_project = db.query(Project).filter_by(id=data["id"]).first()
    assert db_project is not None
    assert db_project.status == ProjectStatus.DRAFT
    assert db_project.genre == BookGenre.FICTION
    
    print(f"\n✅ Project creation with enum fix successful!")
    print(f"   Project ID: {data['id']}")
    print(f"   Status (DB): {db_project.status.value}")
    print(f"   Genre (DB): {db_project.genre.value}") 