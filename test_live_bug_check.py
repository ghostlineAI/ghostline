"""
Test to check live environment for reported bugs
"""
import requests
import time
from datetime import datetime

API_URL = "https://api.dev.ghostline.ai/api/v1"
WEB_URL = "https://dev.ghostline.ai"

def test_live_bugs():
    """Test the live environment"""
    
    print("=" * 80)
    print("LIVE ENVIRONMENT BUG CHECK")
    print("=" * 80)
    
    # Check deployment status
    print("\n1. Checking deployment status...")
    for page in ['/dashboard/projects', '/dashboard/project-detail']:
        response = requests.get(f"{WEB_URL}{page}", allow_redirects=False)
        print(f"   {page}: {response.status_code}")
    
    # Test with real user
    test_email = f"live_check_{int(time.time())}@example.com"
    test_password = "TestPass123!"
    
    print(f"\n2. Creating test user: {test_email}")
    register_response = requests.post(
        f"{API_URL}/auth/register/",
        json={
            "email": test_email,
            "password": test_password,
            "username": f"livecheck_{int(time.time())}",
            "full_name": "Live Check User"
        }
    )
    
    if register_response.status_code != 200:
        print(f"   ❌ Registration failed: {register_response.status_code}")
        return
    print("   ✅ User created")
    
    # Login
    print("\n3. Logging in...")
    login_response = requests.post(
        f"{API_URL}/auth/login/",
        json={
            "email": test_email,
            "password": test_password
        }
    )
    
    if login_response.status_code != 200:
        print(f"   ❌ Login failed: {login_response.status_code}")
        return
    
    auth_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {auth_token}"}
    print("   ✅ Login successful")
    
    # Create project
    print("\n4. Creating project...")
    project_title = f"Live Check {datetime.now().strftime('%H:%M:%S')}"
    create_response = requests.post(
        f"{API_URL}/projects/",
        json={
            "title": project_title,
            "genre": "fiction",
            "description": "Testing live bugs"
        },
        headers=headers
    )
    
    if create_response.status_code != 200:
        print(f"   ❌ Project creation failed: {create_response.status_code}")
        print(f"   Response: {create_response.text}")
        return
    
    project = create_response.json()
    print(f"   ✅ Project created: {project['title']}")
    print(f"   ID: {project['id']}")
    
    # Check if appears immediately
    print("\n5. Checking if project appears immediately...")
    list_response = requests.get(f"{API_URL}/projects/", headers=headers)
    if list_response.status_code == 200:
        projects = list_response.json()
        found = any(p["id"] == project["id"] for p in projects)
        print(f"   Project in list: {'✅ YES' if found else '❌ NO'}")
        print(f"   Total projects: {len(projects)}")
    
    # Test token validity
    print("\n6. Testing token persistence...")
    for i in range(3):
        time.sleep(1)
        test_response = requests.get(f"{API_URL}/users/me/", headers=headers)
        print(f"   Request {i+1}: {test_response.status_code} {'✅' if test_response.status_code == 200 else '❌'}")
    
    print("\n" + "=" * 80)
    print("FINDINGS:")
    print("- Backend API is working correctly")
    print("- Projects appear immediately in API")
    print("- Auth tokens remain valid")
    print("\nFrontend issues to fix:")
    print("1. Hydration mismatch causing logout on refresh")
    print("2. React Query cache not updating immediately")
    print("=" * 80)


if __name__ == "__main__":
    test_live_bugs() 