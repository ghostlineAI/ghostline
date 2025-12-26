"""
Real E2E test for project creation - NO MOCKS
This test hits the actual dev environment
"""
import os

import pytest
import requests
import uuid
import time


RUN_LIVE = os.getenv("RUN_LIVE_DEV_E2E", "").lower() in ("1", "true", "yes")
pytestmark = pytest.mark.skipif(
    not RUN_LIVE,
    reason="Requires live dev environment (set RUN_LIVE_DEV_E2E=1 to enable).",
)


class TestProjectCreationE2E:
    """Real e2e tests against live dev environment"""
    
    BASE_URL = "https://api.dev.ghostline.ai/api/v1"
    
    @pytest.fixture(scope="class")
    def test_user(self):
        """Create a real user for testing"""
        email = f"e2e_pytest_{uuid.uuid4().hex[:8]}@example.com"
        password = "TestPassword123!"
        
        # Register user
        response = requests.post(
            f"{self.BASE_URL}/auth/register",
            json={
                "email": email,
                "password": password,
                "username": f"e2e_user_{int(time.time())}",
                "full_name": "E2E Pytest User"
            }
        )
        assert response.status_code == 200, f"Registration failed: {response.text}"
        
        # Login to get token
        login_response = requests.post(
            f"{self.BASE_URL}/auth/login",
            json={
                "email": email,
                "password": password
            }
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        return {
            "email": email,
            "password": password,
            "token": login_response.json()["access_token"]
        }
    
    def test_create_project_real_api(self, test_user):
        """Test creating a project on the real API"""
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        
        # Create project
        project_data = {
            "title": f"E2E Pytest Project {int(time.time())}",
            "genre": "fiction",
            "description": "Real e2e test project from pytest",
            "target_audience": "general",
            "language": "en"
        }
        
        response = requests.post(
            f"{self.BASE_URL}/projects",
            json=project_data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Project creation failed: {response.text}"
        
        project = response.json()
        assert "id" in project
        assert project["title"] == project_data["title"]
        assert project["genre"] == project_data["genre"]
        assert project["status"] == "draft"
        
        return project["id"]
    
    def test_list_projects_shows_created_project(self, test_user):
        """Test that created project appears in list"""
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        
        # Create a project first
        project_data = {
            "title": f"List Test Project {int(time.time())}",
            "genre": "non_fiction",
            "description": "Testing project listing"
        }
        
        create_response = requests.post(
            f"{self.BASE_URL}/projects",
            json=project_data,
            headers=headers
        )
        assert create_response.status_code == 200
        created_id = create_response.json()["id"]
        
        # List projects
        list_response = requests.get(
            f"{self.BASE_URL}/projects",
            headers=headers
        )
        assert list_response.status_code == 200
        
        projects = list_response.json()
        assert isinstance(projects, list)
        
        # Find our project
        found_project = next((p for p in projects if p["id"] == created_id), None)
        assert found_project is not None, "Created project not found in list"
        assert found_project["title"] == project_data["title"]
    
    def test_frontend_redirect_no_404(self):
        """Test that the frontend projects page doesn't return 404"""
        # Test the actual frontend URL
        response = requests.get("https://dev.ghostline.ai/dashboard/projects/", allow_redirects=True)
        assert response.status_code == 200, "Projects page returns 404!"
        
    def test_invalid_genre_returns_error(self, test_user):
        """Test that invalid genre is properly handled"""
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        
        project_data = {
            "title": "Invalid Genre Test",
            "genre": "invalid_genre_value",
            "description": "This should fail"
        }
        
        response = requests.post(
            f"{self.BASE_URL}/projects",
            json=project_data,
            headers=headers
        )
        
        # Should return 422 for validation error
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
    
    def test_missing_title_returns_error(self, test_user):
        """Test that missing required fields are caught"""
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        
        project_data = {
            # Missing title
            "genre": "fiction",
            "description": "Missing title test"
        }
        
        response = requests.post(
            f"{self.BASE_URL}/projects",
            json=project_data,
            headers=headers
        )
        
        assert response.status_code == 422, f"Expected 422 for missing title, got {response.status_code}"
    
    def test_unauthorized_access_rejected(self):
        """Test that requests without auth are rejected"""
        response = requests.get(f"{self.BASE_URL}/projects")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_full_project_creation_flow(self, test_user):
        """Test the complete flow as a user would experience it"""
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        
        # 1. User creates project
        project_data = {
            "title": f"Full Flow Test {int(time.time())}",
            "genre": "fiction",
            "description": "Complete e2e flow test"
        }
        
        create_response = requests.post(
            f"{self.BASE_URL}/projects",
            json=project_data,
            headers=headers
        )
        assert create_response.status_code == 200, f"Creation failed: {create_response.text}"
        
        project_id = create_response.json()["id"]
        
        # 2. Frontend would redirect to projects list (not detail page)
        # This is what we fixed - no more 404!
        frontend_url = "https://dev.ghostline.ai/dashboard/projects/"
        frontend_response = requests.get(frontend_url)
        assert frontend_response.status_code == 200, "Frontend projects page returns 404!"
        
        # 3. Verify project in list
        list_response = requests.get(f"{self.BASE_URL}/projects", headers=headers)
        assert list_response.status_code == 200
        
        projects = list_response.json()
        assert any(p["id"] == project_id for p in projects), "Created project not in list"
        
        print(f"\n✅ Full e2e test passed!")
        print(f"   Created project: {project_data['title']}")
        print(f"   Project ID: {project_id}")
        print(f"   Frontend redirect: {frontend_url} (no 404!)")
        print(f"   Project appears in list: Yes") 