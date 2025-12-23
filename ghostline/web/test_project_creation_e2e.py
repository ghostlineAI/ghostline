#!/usr/bin/env python3
"""
Real E2E test for project creation flow
Tests against the live dev environment
"""

import requests
import time
import uuid

# Test configuration
BASE_URL = "https://api.dev.ghostline.ai/api/v1"
TEST_EMAIL = f"e2e_test_{uuid.uuid4().hex[:8]}@example.com"
TEST_PASSWORD = "TestPassword123!"

def test_project_creation_e2e():
    """Test the complete project creation flow on dev environment"""
    
    print(f"\n=== Starting E2E Test for Project Creation ===")
    print(f"Environment: {BASE_URL}")
    print(f"Test Email: {TEST_EMAIL}")
    
    # Step 1: Register a new user
    print("\n1. Registering new user...")
    register_response = requests.post(
        f"{BASE_URL}/auth/register/",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "username": f"e2e_user_{int(time.time())}",
            "full_name": "E2E Test User"
        }
    )
    
    if register_response.status_code != 200:
        print(f"❌ Registration failed: {register_response.status_code}")
        print(f"Response: {register_response.text}")
        return False
    
    print("✅ User registered successfully")
    
    # Step 2: Login to get auth token
    print("\n2. Logging in...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login/",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(f"Response: {login_response.text}")
        return False
    
    auth_token = login_response.json()["access_token"]
    print("✅ Login successful")
    
    # Step 3: Create a project
    print("\n3. Creating project...")
    project_data = {
        "title": f"E2E Test Project {int(time.time())}",
        "genre": "fiction",
        "description": "This is an automated e2e test project",
        "target_audience": "general",
        "language": "en"
    }
    
    create_response = requests.post(
        f"{BASE_URL}/projects/",
        json=project_data,
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    if create_response.status_code != 200:
        print(f"❌ Project creation failed: {create_response.status_code}")
        print(f"Response: {create_response.text}")
        
        # Check if it's the 500 error that appears as CORS
        if create_response.status_code == 500:
            print("\n⚠️  This might be the CORS/500 error pattern mentioned in the blueprint")
            print("Check if 'fiction' is a valid enum value in the database")
        
        return False
    
    project_id = create_response.json()["id"]
    print(f"✅ Project created successfully with ID: {project_id}")
    
    # Step 4: List projects to verify
    print("\n4. Verifying project appears in list...")
    list_response = requests.get(
        f"{BASE_URL}/projects/",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    if list_response.status_code != 200:
        print(f"❌ Failed to list projects: {list_response.status_code}")
        return False
    
    projects = list_response.json()
    created_project = next((p for p in projects if p["id"] == project_id), None)
    
    if not created_project:
        print("❌ Created project not found in list")
        return False
    
    print(f"✅ Project found in list: {created_project['title']}")
    print(f"   Status: {created_project['status']}")
    print(f"   Genre: {created_project['genre']}")
    
    # Step 5: Test the UI navigation (simulate what happens after creation)
    print("\n5. Testing UI navigation after creation...")
    print(f"   Frontend would redirect to: https://dev.ghostline.ai/dashboard/projects")
    print(f"   (No longer redirecting to /dashboard/projects/{project_id} due to static export)")
    
    # Step 6: Verify no 404 errors
    print("\n6. Verifying no 404 errors...")
    dashboard_response = requests.get("https://dev.ghostline.ai/dashboard/projects")
    
    if dashboard_response.status_code == 404:
        print("❌ Dashboard projects page returns 404!")
        return False
    
    print("✅ Dashboard projects page accessible (no 404)")
    
    # Test complete
    print("\n=== E2E Test Complete ===")
    print("✅ All tests passed!")
    print("\nSummary:")
    print(f"- Created user: {TEST_EMAIL}")
    print(f"- Created project: {project_data['title']}")
    print(f"- Project ID: {project_id}")
    print("- No 404 errors after project creation")
    print("- Users would be redirected to projects list page")
    
    return True


if __name__ == "__main__":
    success = test_project_creation_e2e()
    exit(0 if success else 1) 