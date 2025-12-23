"""
E2E tests for data room functionality.
Tests upload, list, view, and delete operations for source materials.
"""

import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.project import Project, ProjectStatus, BookGenre
from app.services.auth import AuthService

# Test file paths
TEST_FILES_DIR = Path(__file__).parent / "test_files"


@pytest.fixture
def test_files():
    """Create test files for upload."""
    # Create test files directory if it doesn't exist
    TEST_FILES_DIR.mkdir(exist_ok=True)
    
    # Create test files
    test_txt = TEST_FILES_DIR / "test_document.txt"
    test_txt.write_text("This is a test document for the data room E2E test.")
    
    test_pdf = TEST_FILES_DIR / "test_document.pdf"
    # Create a minimal PDF (PDF header + empty content + EOF)
    test_pdf.write_bytes(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\nxref\n0 3\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\ntrailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n116\n%%EOF")
    
    yield {
        "txt": test_txt,
        "pdf": test_pdf,
    }
    
    # Cleanup
    for file in TEST_FILES_DIR.glob("test_*"):
        file.unlink()


@pytest.fixture
def test_user_with_project(db: Session, client: TestClient):
    """Create a test user with a project."""
    # Create user
    user = User(
        email="dataroom_test@example.com",
        username="dataroom_test",
        hashed_password=AuthService.get_password_hash("TestPassword123!"),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create project
    project = Project(
        title="Data Room Test Project",
        description="Project for testing data room functionality",
        owner_id=user.id,
        status=ProjectStatus.DRAFT,
        genre=BookGenre.OTHER,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Login to get token
    login_data = {
        "email": "dataroom_test@example.com",
        "password": "TestPassword123!"
    }
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    yield {
        "user": user,
        "project": project,
        "headers": headers,
    }
    
    # Cleanup is handled by database rollback


def test_upload_list_and_delete_materials(
    client: TestClient,
    test_user_with_project,
    test_files,
    db: Session
):
    """Test the complete data room workflow: upload, list, and delete materials."""
    user_data = test_user_with_project
    project = user_data["project"]
    headers = user_data["headers"]
    
    # Test 1: Upload text file
    with open(test_files["txt"], "rb") as f:
        response = client.post(
            "/api/v1/source-materials/upload",
            files={"file": ("test_document.txt", f, "text/plain")},
            data={"project_id": str(project.id)},
            headers=headers,
        )
    
    assert response.status_code == 200
    txt_upload = response.json()
    assert txt_upload["name"] == "test_document.txt"
    assert txt_upload["type"] == "txt"
    assert txt_upload["size"] > 0
    assert "id" in txt_upload
    txt_material_id = txt_upload["id"]
    
    # Test 2: Upload PDF file
    with open(test_files["pdf"], "rb") as f:
        response = client.post(
            "/api/v1/source-materials/upload",
            files={"file": ("test_document.pdf", f, "application/pdf")},
            data={"project_id": str(project.id)},
            headers=headers,
        )
    
    assert response.status_code == 200
    pdf_upload = response.json()
    assert pdf_upload["name"] == "test_document.pdf"
    assert pdf_upload["type"] == "pdf"
    pdf_material_id = pdf_upload["id"]
    
    # Test 3: List materials for the project
    response = client.get(
        f"/api/v1/projects/{project.id}/source-materials",
        headers=headers,
    )
    
    assert response.status_code == 200
    materials = response.json()
    assert len(materials) == 2
    
    # Verify material details
    material_filenames = [m["filename"] for m in materials]
    assert "test_document.txt" in material_filenames
    assert "test_document.pdf" in material_filenames
    
    # Check material properties
    for material in materials:
        assert "id" in material
        assert "filename" in material
        assert "material_type" in material
        assert "file_size" in material
        assert "processing_status" in material
        assert "created_at" in material
    
    # Test 4: Get specific material
    response = client.get(
        f"/api/v1/source-materials/{txt_material_id}",
        headers=headers,
    )
    
    assert response.status_code == 200
    material = response.json()
    assert material["filename"] == "test_document.txt"
    assert material["material_type"] == "TEXT"
    
    # Test 5: Delete text file
    response = client.delete(
        f"/api/v1/source-materials/{txt_material_id}",
        headers=headers,
    )
    
    assert response.status_code == 200
    assert response.json()["detail"] == "Source material deleted successfully"
    
    # Test 6: Verify deletion - list should now have only 1 material
    response = client.get(
        f"/api/v1/projects/{project.id}/source-materials",
        headers=headers,
    )
    
    assert response.status_code == 200
    materials = response.json()
    assert len(materials) == 1
    assert materials[0]["filename"] == "test_document.pdf"
    
    # Test 7: Try to get deleted material (should fail)
    response = client.get(
        f"/api/v1/source-materials/{txt_material_id}",
        headers=headers,
    )
    
    assert response.status_code == 404
    
    # Test 8: Delete PDF file
    response = client.delete(
        f"/api/v1/source-materials/{pdf_material_id}",
        headers=headers,
    )
    
    assert response.status_code == 200
    
    # Test 9: Verify all materials are deleted
    response = client.get(
        f"/api/v1/projects/{project.id}/source-materials",
        headers=headers,
    )
    
    assert response.status_code == 200
    materials = response.json()
    assert len(materials) == 0


def test_upload_duplicate_file(
    client: TestClient,
    test_user_with_project,
    test_files,
):
    """Test uploading a duplicate file."""
    user_data = test_user_with_project
    project = user_data["project"]
    headers = user_data["headers"]
    
    # Upload file first time
    with open(test_files["txt"], "rb") as f:
        response = client.post(
            "/api/v1/source-materials/upload",
            files={"file": ("test_document.txt", f, "text/plain")},
            data={"project_id": str(project.id)},
            headers=headers,
        )
    
    assert response.status_code == 200
    first_upload = response.json()
    
    # Upload same file again
    with open(test_files["txt"], "rb") as f:
        response = client.post(
            "/api/v1/source-materials/upload",
            files={"file": ("test_document.txt", f, "text/plain")},
            data={"project_id": str(project.id)},
            headers=headers,
        )
    
    assert response.status_code == 200
    duplicate_upload = response.json()
    
    # Should indicate it's a duplicate
    assert duplicate_upload.get("duplicate") is True
    assert duplicate_upload.get("message") == "File already exists"
    assert duplicate_upload["id"] == first_upload["id"]


def test_upload_invalid_file_type(
    client: TestClient,
    test_user_with_project,
):
    """Test uploading an invalid file type."""
    user_data = test_user_with_project
    project = user_data["project"]
    headers = user_data["headers"]
    
    # Create a file with invalid extension
    invalid_file = TEST_FILES_DIR / "test.xyz"
    invalid_file.write_text("Invalid file type")
    
    try:
        with open(invalid_file, "rb") as f:
            response = client.post(
                "/api/v1/source-materials/upload",
                files={"file": ("test.xyz", f, "application/octet-stream")},
                data={"project_id": str(project.id)},
                headers=headers,
            )
        
        assert response.status_code == 400
        assert "File type not allowed" in response.json()["detail"]
    finally:
        invalid_file.unlink()


def test_upload_oversized_file(
    client: TestClient,
    test_user_with_project,
):
    """Test uploading a file that exceeds size limit."""
    user_data = test_user_with_project
    project = user_data["project"]
    headers = user_data["headers"]
    
    # Create a large file (> 50MB)
    large_file = TEST_FILES_DIR / "large_file.txt"
    large_file.write_bytes(b"x" * (51 * 1024 * 1024))  # 51MB
    
    try:
        with open(large_file, "rb") as f:
            response = client.post(
                "/api/v1/source-materials/upload",
                files={"file": ("large_file.txt", f, "text/plain")},
                data={"project_id": str(project.id)},
                headers=headers,
            )
        
        assert response.status_code == 400
        assert "File too large" in response.json()["detail"]
    finally:
        large_file.unlink()


def test_unauthorized_access(
    client: TestClient,
    test_user_with_project,
    test_files,
    db: Session,
):
    """Test that users cannot access materials from other users' projects."""
    user_data = test_user_with_project
    project = user_data["project"]
    headers = user_data["headers"]
    
    # Upload a file
    with open(test_files["txt"], "rb") as f:
        response = client.post(
            "/api/v1/source-materials/upload",
            files={"file": ("test_document.txt", f, "text/plain")},
            data={"project_id": str(project.id)},
            headers=headers,
        )
    
    assert response.status_code == 200
    material_id = response.json()["id"]
    
    # Create another user
    other_user = User(
        email="other_user@example.com",
        username="other_user",
        hashed_password=AuthService.get_password_hash("OtherPassword123!"),
        is_active=True,
        is_verified=True,
    )
    db.add(other_user)
    db.commit()
    
    # Login as other user to get token
    login_data = {
        "email": "other_user@example.com",
        "password": "OtherPassword123!"
    }
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    other_token = response.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}
    
    # Try to access the material with other user's token
    response = client.get(
        f"/api/v1/source-materials/{material_id}",
        headers=other_headers,
    )
    
    assert response.status_code == 404  # Should not be found for other user
    
    # Try to delete the material with other user's token
    response = client.delete(
        f"/api/v1/source-materials/{material_id}",
        headers=other_headers,
    )
    
    assert response.status_code == 404  # Should not be found for other user 