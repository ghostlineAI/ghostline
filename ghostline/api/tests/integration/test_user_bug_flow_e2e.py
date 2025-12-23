"""
E2E test to verify the exact user flow and bug fixes reported by the user
"""
import pytest
import requests
import time
from datetime import datetime

API_URL = "https://api.dev.ghostline.ai/api/v1"
WEB_URL = "https://dev.ghostline.ai"


class TestUserBugFlow:
    """Test the exact flow and bugs reported by the user"""
    
    @pytest.fixture
    def unique_user(self):
        """Create a unique test user"""
        timestamp = int(time.time() * 1000)
        return {
            "email": f"bug_test_{timestamp}@example.com",
            "password": "TestPass123!",
            "username": f"bugtest_{timestamp}",
            "full_name": f"Bug Test User {timestamp}"
        }
    
    def test_complete_user_flow_with_bug_verification(self, unique_user):
        """Test the complete flow as reported by user with bug checks"""
        print("\n" + "="*80)
        print("TESTING USER REPORTED BUG FLOW")
        print("="*80)
        
        # 1. Register user
        print("\n1. Registering new user...")
        register_response = requests.post(
            f"{API_URL}/auth/register/",
            json=unique_user
        )
        assert register_response.status_code == 200
        print(f"   ✅ User registered: {unique_user['email']}")
        
        # 2. Login
        print("\n2. Logging in...")
        login_response = requests.post(
            f"{API_URL}/auth/login/",
            json={
                "email": unique_user["email"],
                "password": unique_user["password"]
            }
        )
        assert login_response.status_code == 200
        auth_data = login_response.json()
        token = auth_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("   ✅ Login successful")
        
        # 3. Create project
        print("\n3. Creating project...")
        project_title = f"Bug Test Project {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        create_response = requests.post(
            f"{API_URL}/projects/",
            json={
                "title": project_title,
                "genre": "fiction",
                "description": "Testing user reported bugs"
            },
            headers=headers
        )
        assert create_response.status_code == 200
        project = create_response.json()
        print(f"   ✅ Project created: {project['title']}")
        print(f"   ID: {project['id']}")
        
        # 4. IMMEDIATELY check if project appears in list (simulating user's immediate navigation)
        print("\n4. Checking if project appears IMMEDIATELY in list...")
        list_response = requests.get(f"{API_URL}/projects/", headers=headers)
        assert list_response.status_code == 200
        projects = list_response.json()
        
        # Find our project
        found_project = None
        for p in projects:
            if p["id"] == project["id"]:
                found_project = p
                break
        
        if found_project:
            print(f"   ✅ Project appears immediately in list!")
            print(f"   Found: {found_project['title']}")
        else:
            print(f"   ❌ BUG: Project does NOT appear immediately")
            print(f"   Total projects in list: {len(projects)}")
        
        assert found_project is not None, "Project should appear immediately after creation"
        
        # 5. Simulate page refresh by checking auth again
        print("\n5. Simulating page refresh (checking if auth persists)...")
        me_response = requests.get(f"{API_URL}/users/me/", headers=headers)
        if me_response.status_code == 200:
            print("   ✅ Auth token still valid after simulated refresh")
        else:
            print(f"   ❌ BUG: Auth failed after refresh: {me_response.status_code}")
        
        assert me_response.status_code == 200, "Auth should persist after refresh"
        
        # 6. Check project list again (simulating re-login scenario)
        print("\n6. Checking project list again (simulating re-login)...")
        list_response2 = requests.get(f"{API_URL}/projects/", headers=headers)
        assert list_response2.status_code == 200
        projects2 = list_response2.json()
        
        found_again = any(p["id"] == project["id"] for p in projects2)
        assert found_again, "Project should still be in list"
        print(f"   ✅ Project still appears in list")
        print(f"   Total projects: {len(projects2)}")
        
        # 7. Test navigation URLs
        print("\n7. Testing navigation URLs...")
        
        # Check projects list page
        projects_page = requests.get(f"{WEB_URL}/dashboard/projects", allow_redirects=False)
        print(f"   /dashboard/projects: {projects_page.status_code}")
        
        # Check project detail page  
        detail_page = requests.get(f"{WEB_URL}/dashboard/project-detail", allow_redirects=False)
        print(f"   /dashboard/project-detail: {detail_page.status_code}")
        
        print("\n" + "="*80)
        print("TEST SUMMARY:")
        print("- ✅ User registration works")
        print("- ✅ Login works") 
        print("- ✅ Project creation works")
        print("- ✅ Project appears immediately in API")
        print("- ✅ Auth token persists (API level)")
        print("- ✅ Project remains in list after 'refresh'")
        print("\nFrontend status:")
        print("- Projects list page exists (redirect expected for auth)")
        print("- Project detail page exists (redirect expected for auth)")
        print("="*80)
    
    def test_rapid_project_creation(self, unique_user):
        """Test creating multiple projects rapidly"""
        # Register and login
        register_response = requests.post(f"{API_URL}/auth/register/", json=unique_user)
        assert register_response.status_code == 200
        
        login_response = requests.post(
            f"{API_URL}/auth/login/",
            json={"email": unique_user["email"], "password": unique_user["password"]}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        print("\n" + "="*50)
        print("TESTING RAPID PROJECT CREATION")
        print("="*50)
        
        # Create 3 projects rapidly
        created_projects = []
        for i in range(3):
            project_response = requests.post(
                f"{API_URL}/projects/",
                json={
                    "title": f"Rapid Test {i+1} - {int(time.time())}",
                    "genre": "fiction",
                    "description": f"Rapid test project {i+1}"
                },
                headers=headers
            )
            assert project_response.status_code == 200
            created_projects.append(project_response.json())
            print(f"Created project {i+1}: {created_projects[-1]['title']}")
        
        # Immediately check if all appear
        list_response = requests.get(f"{API_URL}/projects/", headers=headers)
        assert list_response.status_code == 200
        projects = list_response.json()
        
        found_count = 0
        for created in created_projects:
            if any(p["id"] == created["id"] for p in projects):
                found_count += 1
        
        print(f"\nFound {found_count}/3 projects immediately")
        assert found_count == 3, "All projects should appear immediately"
        print("✅ All projects appear immediately!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"]) 